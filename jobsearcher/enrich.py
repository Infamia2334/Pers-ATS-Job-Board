"""Optional Gemini Flash-Lite enrichment of surviving job rows.

OFF unless both of these hold: GEMINI_API_KEY is in the process
environment and the `google-genai` package is importable — the key is
never read from config.toml (that file ships to the public repo), and a
missing SDK just silently disables the feature with a one-line hint.

Design ground rules:

- Annotation, never gating. The deterministic regex pipeline in
  config.py decides what's in or out; the model only adds advisory fields
  (AI_YOE / AI_Remote / AI_Salary / AI_Stack / AI_Note) to rows that
  already passed, so scrapes stay reproducible and an API outage can only
  blank a badge column, never lose postings.
- Only NEW rows are annotated. Rows whose URL appeared in the previous
  snapshot adopt the previous annotation unchanged (no repeat spend); the
  per-run annotation count is capped by [enrich].max_jobs, and rows past
  the cap stay blank and get annotated on a later run.
- Only description-holding rows are annotated (ATS boards + HN/RemoteOK/
  WWR/Zoho). YC and LinkedIn guest cards have no JD text and stay blank.
- Failures degrade to blank fields — same silent-failure philosophy as
  the rest of the fetch layer.

`AI_Done` marks an annotation as final so a carried-forward row is never
re-called; it rides through the snapshot like every other AI_* field and
is ignored by the CSV writer (extrasaction="ignore") and the UI.

The scraper core stays stdlib-only; this module is the one place that
imports an external package (requirements.txt: google-genai).
"""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from google import genai as genai_sdk
    from google.genai import types as gtypes
except ImportError:
    genai_sdk = None
    gtypes = None

from .config import (ENRICH_CONCURRENCY, ENRICH_MAX_DESC_CHARS,
                     ENRICH_MAX_JOBS, ENRICH_TIMEOUT, ENRICH_MODEL)

_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

if genai_sdk is None and _API_KEY:
    print("NOTE: GEMINI_API_KEY is set but google-genai is not installed — "
          "run `pip install -r requirements.txt` to enable AI enrichment.",
          file=sys.stderr)

AVAILABLE = bool(_API_KEY) and bool(ENRICH_MODEL) and genai_sdk is not None
_CLIENT = None
if AVAILABLE:
    _CLIENT = genai_sdk.Client(
        api_key=_API_KEY,
        http_options=gtypes.HttpOptions(timeout=ENRICH_TIMEOUT * 1000))

_BLANK = {"AI_YOE": "n/a", "AI_Remote": "", "AI_Salary": "",
          "AI_Stack": "", "AI_Note": "", "AI_Done": False}

_INSTRUCTION = """You are annotating a job posting for an engineer who caps at 2 years of
experience and targets remote-first backend / platform / AI-infra /
distributed-systems roles. Read the posting below and return ONLY a
compact JSON object, no markdown, in exactly this shape:

{"stated_yoe": <integer or null — the LEAST years of experience the
   posting asks for, only when a number of years is actually stated>,
 "yoe_stance": "<required|preferred|unmentioned>",
 "remote_policy": "<remote-global|remote-region|hybrid|onsite|unclear>",
 "salary": "<salary exactly as stated, e.g. \\"$120,000-$150,000\\"; empty
   string if absent>",
 "stack": ["up to 6 short tech keywords actually mentioned, in order
   of prominence"],
 "note": "<one sentence, max 200 chars: what this role is and who it
   fits>"}"""


def _payload_text(row: dict) -> str:
    desc = (row.get("_desc") or "")[:ENRICH_MAX_DESC_CHARS]
    return (f"Title: {row.get('Title', '')}\n"
            f"Company: {row.get('Company', '')}\n"
            f"Location field: {row.get('Location', '')}\n"
            f"Posting text:\n{desc}\n\n" + _INSTRUCTION)


def _parse_json(text: str) -> dict | None:
    """Tolerant fallback parser: strips fences, grabs the outermost object."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`\n ")
        if t.lower().startswith("json"):
            t = t[4:].lstrip()
    if "{" not in t or "}" not in t:
        return None
    t = t[t.index("{"):t.rindex("}") + 1]
    try:
        data = json.loads(t)
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _fill(row: dict, data: dict) -> None:
    yoe = data.get("stated_yoe")
    stance = str(data.get("yoe_stance") or "unmentioned").strip()
    row["AI_YOE"] = (f"{int(yoe)} {stance}" if isinstance(yoe, int)
                     and 0 <= yoe <= 20 else "n/a")
    row["AI_Remote"] = str(data.get("remote_policy") or "").strip() \
        .lower().replace(" ", "-")
    row["AI_Salary"] = str(data.get("salary") or "").strip()
    stack = data.get("stack")
    if isinstance(stack, list):
        row["AI_Stack"] = ", ".join(str(s).strip() for s in stack
                                    if str(s).strip())[:120]
    note = str(data.get("note") or "").strip()[:220]
    if note:
        row["AI_Note"] = note
    row["AI_Done"] = True


def _annotate(row: dict) -> None:
    """One API call; fills AI_* on `row`. Any failure leaves them blank."""
    try:
        resp = _CLIENT.models.generate_content(
            model=ENRICH_MODEL,
            contents=[_payload_text(row)],
            config=gtypes.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                max_output_tokens=500),
        )
    except Exception:  # 429/5xx/timeout/unit errors — degrade to blanks
        return
    data = resp.parsed if isinstance(getattr(resp, "parsed", None), dict) \
        else _parse_json(getattr(resp, "text", ""))
    if data:
        _fill(row, data)


def enrich_jobs(rows: list, prev_by_url: dict | None = None) -> tuple:
    """Attach AI_* fields; returns (rows, newly_annotated_count).

    `prev_by_url` maps apply URL -> previously enriched row (from the web
    mode's last scrape). Matching URLs adopt the old annotation as-is;
    unmatched rows with a description go to the model under a small pool,
    capped at [enrich].max_jobs calls this run.
    """
    total = 0
    if AVAILABLE:
        prev_by_url = prev_by_url or {}
        todo = []
        for row in rows:
            prev = prev_by_url.get((row.get("Direct_Apply_URL") or "")
                                   .strip().rstrip("/"))
            if prev is not None and prev.get("AI_Done"):
                for k, v in prev.items():
                    if k.startswith("AI_"):
                        row[k] = v
                continue
            for k, v in _BLANK.items():
                row.setdefault(k, v)
            if (row.get("_desc") or "").strip() and len(todo) < ENRICH_MAX_JOBS:
                todo.append(row)
        if todo:
            with ThreadPoolExecutor(max_workers=ENRICH_CONCURRENCY) as ex:
                futs = [ex.submit(_annotate, r) for r in todo]
                for fut in as_completed(futs):
                    fut.result()
            total = len(todo)
    else:
        for row in rows:
            for k, v in _BLANK.items():
                row.setdefault(k, v)
    return rows, total


def ai_fieldnames() -> list:
    """Column names, in row order, for the CSV writer."""
    return ["AI_YOE", "AI_Remote", "AI_Salary", "AI_Stack", "AI_Note"]
