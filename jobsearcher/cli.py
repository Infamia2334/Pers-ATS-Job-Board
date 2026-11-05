"""Command-line entry points: CSV mode and board/feed liveness verification."""

import csv
import html
import json
import os
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from .config import (CFG, CONFIG_PATH, MAX_WORKERS, PREVIEW_COUNT,
                     LIVE_FEED_PATH_CFG, _SCRIPT_DIR)
from .fetch import fetch_json, fetch_text
from .sources import _zoho_site_entries
from .engine import collect_jobs

CSV_FIELDNAMES = ["ATS", "Company", "Title", "Location", "Max_Stated_YOE",
                  "Recommended_PDF", "Direct_Apply_URL"]


def main():
    all_jobs = collect_jobs()

    # Default to a CSV next to this script; config [run].live_feed_path then
    # env LIVE_FEED_PATH override, in that order.
    out_path = LIVE_FEED_PATH_CFG and os.path.join(_SCRIPT_DIR, LIVE_FEED_PATH_CFG) \
        or os.environ.get("LIVE_FEED_PATH", "") \
        or os.path.join(_SCRIPT_DIR, "Live_Openings_Feed.csv")
    if not os.path.isabs(out_path):
        out_path = os.path.join(_SCRIPT_DIR, out_path)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_jobs)

    sources = []
    if CFG["boards"]["ashby"].get("enabled"):
        sources.append("Ashby")
    if CFG["boards"]["greenhouse"].get("enabled"):
        sources.append("Greenhouse")
    if CFG["boards"]["lever"].get("enabled"):
        sources.append("Lever")
    for name in ("yc", "hn", "remoteok", "weworkremotely", "linkedin", "zoho"):
        if CFG["feeds"][name].get("enabled"):
            sources.append(name)
    print(f"Config: {CONFIG_PATH}")
    print(f"Found {len(all_jobs)} live matching openings across "
          f"{', '.join(sources) or 'no enabled sources'}.")
    print(f"Saved to {out_path}")
    companies = sorted(set(j["Company"] for j in all_jobs))
    print(f"{len(companies)} distinct companies: {', '.join(companies)}\n")
    print("Top matches (one row per company, priority-tier order):")
    seen_companies = set()
    preview = []
    for j in all_jobs:
        if j["Company"] in seen_companies:
            continue
        seen_companies.add(j["Company"])
        preview.append(j)
        if len(preview) == PREVIEW_COUNT:
            break
    for idx, j in enumerate(preview, 1):
        print(f"{idx:02d}. [{j['ATS']}] {j['Company']} — {j['Title']} ({j['Location']})\n    {j['Direct_Apply_URL']}")


def verify_boards():
    """Check every enabled board slug and feed; report dead/empty ones."""
    ats_boards = CFG["boards"]
    tasks = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        if ats_boards["ashby"].get("enabled"):
            for s in ats_boards["ashby"].get("boards", []):
                tasks.append(("Ashby", s,
                              ex.submit(fetch_json, f"https://api.ashbyhq.com/posting-api/job-board/{s}")))
        if ats_boards["greenhouse"].get("enabled"):
            for s in ats_boards["greenhouse"].get("boards", []):
                tasks.append(("Greenhouse", s,
                              ex.submit(fetch_json, f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs?content=true")))
        if ats_boards["lever"].get("enabled"):
            for s in ats_boards["lever"].get("boards", []):
                tasks.append(("Lever", s,
                              ex.submit(fetch_json, f"https://api.lever.co/v0/postings/{s}?mode=json")))
        rows = list(tasks)

    def retry_url(ats, slug):
        if ats == "Greenhouse":
            return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        if ats == "Lever":
            return f"https://api.lever.co/v0/postings/{slug}?mode=json"
        return f"https://api.ashbyhq.com/posting-api/job-board/{slug}"

    def probe(ats, slug, fut):
        try:
            data = fut.result()
            n = len(data) if isinstance(data, list) else len(data.get("jobs", []))
            return (ats, slug, n, None)
        except Exception as e:
            if "timed out" in str(e).lower():
                # Transient under high concurrency — one retry before verdict.
                try:
                    data = fetch_json(retry_url(ats, slug))
                    n = len(data) if isinstance(data, list) else len(data.get("jobs", []))
                    return (ats, slug, n, None)
                except Exception as e2:
                    return (ats, slug, None, str(e2))
            return (ats, slug, None, str(e))

    dead, empty, alive = [], [], 0
    for ats, slug, fut in rows:
        ats, slug, n, err = probe(ats, slug, fut)
        if err:
            dead.append((ats, slug, err))
        elif n == 0:
            empty.append((ats, slug))
        else:
            alive += 1
            print(f"  ok    [{ats:9s}] {slug:24s} {n} postings")
    if empty:
        print("\nEmpty boards (live but 0 postings — prune or keep an eye on):")
        for ats, slug in empty:
            print(f"  empty [{ats:9s}] {slug}")
    if dead:
        print("\nDead boards (wrong slug, moved, or deleted):")
        for ats, slug, err in dead:
            print(f"  dead  [{ats:9s}] {slug:24s} {err[:60]}")
    print(f"\n{alive} live boards, {len(empty)} empty, {len(dead)} dead.")

    print("\nNon-ATS sources:")
    print(_probe_source_liveness())


def _probe_source_liveness():
    """Liveness smoke test for the enabled non-ATS feeds; printable string."""
    feeds = CFG["feeds"]
    lines = []

    def alive(name, _err=""):
        lines.append(f"  ok    {name}")

    def dead(name, err):
        lines.append(f"  dead  {name}: {err[:70] if err else ''}")

    if feeds["yc"].get("enabled"):
        try:
            page = fetch_text("https://www.workatastartup.com/jobs?roles=eng")
            blob = re.search(r'data-page="([^"]+)"', page)
            n = len(json.loads(html.unescape(blob.group(1))).get("props", {}).get("jobs", [])) if blob else 0
            (alive if n > 0 else dead)("YC jobs page", "" if n else "no data-page/jobs")
        except Exception as e:
            dead("YC jobs page", str(e))
    if feeds["hn"].get("enabled"):
        try:
            data = fetch_json("https://hn.algolia.com/api/v1/search_by_date"
                              "?query=%22Who%20is%20hiring%22&tags=story,author_whoishiring&hitsPerPage=10")
            (alive if data.get("hits") else dead)("HN who-is-hiring", "" if data.get("hits") else "no stories")
        except Exception as e:
            dead("HN who-is-hiring", str(e))
    if feeds["remoteok"].get("enabled"):
        try:
            data = fetch_json("https://remoteok.com/api")
            n = sum(1 for j in data if isinstance(j, dict) and j.get("position"))
            (alive if n > 0 else dead)("RemoteOK", "" if n else "no postings")
        except Exception as e:
            dead("RemoteOK", str(e))
    if feeds["weworkremotely"].get("enabled"):
        for feed in feeds["weworkremotely"].get("feeds", []):
            try:
                raw = fetch_text(f"https://weworkremotely.com/categories/{feed}.rss")
                n = raw.count("<item>")
                (alive if n > 0 else dead)(f"WWR {feed}", "" if n else "no items")
            except Exception as e:
                dead(f"WWR {feed}", str(e))
    if feeds["zoho"].get("enabled"):
        for cfg in _zoho_site_entries():
            try:
                data = fetch_json(
                    f"{cfg['site'].rstrip('/')}/recruit/v2/public/Job_Openings"
                    f"?pagename={urllib.parse.quote(cfg['page_name'])}"
                )
                ok = isinstance(data, dict) and data.get("code") == "success"
                (alive if ok else dead)(f"Zoho {cfg['company']}",
                                        "" if ok else "unexpected response shape")
            except Exception as e:
                dead(f"Zoho {cfg['company']}", str(e))
    if feeds["linkedin"].get("enabled"):
        for i, u in enumerate(feeds["linkedin"].get("queries", []), 1):
            try:
                frag = fetch_text(u)
                n = frag.count("data-entity-urn")
                (alive if n > 0 else dead)(f"LinkedIn query {i}", "" if n else "no cards")
            except Exception as e:
                dead(f"LinkedIn query {i}", str(e))
    return "\n".join(lines)
