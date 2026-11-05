"""Configuration loading and compiled filter constants.

Everything tunable lives in config.toml next to the repository root; the
path can be overridden with the JOB_CONFIG env var. This module loads it
at import time (stdlib tomllib — Python 3.12+) and compiles the filter
regexes plus the per-module constants the rest of the package reads.

A trimmed config still behaves: in-code DEFAULTS are deep-merged under
the file's values, so only keys missing from the TOML get defaults.
"""

import html
import os
import re
import shutil
import subprocess
import sys
import tomllib

# Directory of the *repository* (the package's parent), where config.toml,
# start.sh and the Live_Openings_Feed.csv output live.
_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.environ.get("JOB_CONFIG", os.path.join(_SCRIPT_DIR, "config.toml"))

# Only consulted for keys missing from config.toml, so a trimmed file still
# produces the classic behaviour. config.toml is the real source of truth.
DEFAULTS = {
    "profile": {
        "name": "",
        "headline": "Live engineering openings",
        "summary": "",
        "years_experience": 2,
        "resume_pdf": "work/Resume/resume.pdf",
    },
    "filters": {
        "role_include_keywords": [],
        "role_include_regex": r"\b(backend|back-end|software engineer|member of technical staff"
                              r"|mts|platform|distributed|infrastructure|infra|ai engineer|ai infra"
                              r"|machine learning|ml|llm|systems engineer|sde|product engineer"
                              r"|full[- ]?stack|server|founding|python|node|typescript)\b",
        "role_exclude_keywords": [],
        "role_exclude_regex": r"\b(ios|android|mobile|frontend only|front-end only|account executive"
                              r"|sales|marketing|gtm|recruiter|legal|finance|counsel|designer|copywriter"
                              r"|customer success|support engineer|architect|intern|director|principal"
                              r"|manager|vp|head of|distinguished|lead|senior|sr"
                              r"|staff(?: \w[\w-]*){0,2} engineer|staff sde|staff swe)\b",
        "location_include_keywords": [],
        "location_include_regex": r"\b(bengaluru|bangalore|gurgaon|gurugram|india|remote|global"
                                  r"|anywhere|apac|emea|singapore|bangkok|thailand|amsterdam"
                                  r"|netherlands|berlin|munich|germany|london|uk|tallinn|estonia"
                                  r"|dublin|stockholm|tokyo|japan|europe)\b",
        "location_exclude_regex": r"\b(us only|us-only|united states only|us-remote|americas only"
                                  r"|canada only|brazil|mexico)\b|remote\s*[(\[]?\s*-?\s*u\.?\.?\.?\s*[)\]]?",
        "max_years_experience": 2,
        "location_priority_tiers": [["remote", "global", "anywhere"]],
    },
    "boards": {
        "ashby": {"enabled": False, "boards": []},
        "greenhouse": {"enabled": False, "boards": []},
        "lever": {"enabled": False, "boards": []},
        "companies": {"keep": [], "drop": []},
    },
    "feeds": {
        "yc": {"enabled": False},
        "hn": {"enabled": False},
        "remoteok": {"enabled": False},
        "weworkremotely": {"enabled": False, "feeds": []},
        "linkedin": {"enabled": False, "queries": []},
        "zoho": {"enabled": False, "sites": []},
    },
    "run": {
        "dedup": True,
        "max_workers": 40,
        "timeout_seconds": 15,
        "web_port": 8000,
        "cache_ttl_seconds": 600,
        "snapshot_path": "data/snapshot.json",
        "live_feed_path": "",
        "preview_count": 20,
    },
    "enrich": {
        "model": "gemini-3.5-flash-lite",
        "key": "",
        "key_file": ".env",
        "max_jobs": 60,
        "concurrency": 5,
        "timeout_seconds": 25,
        "max_desc_chars": 6000,
    },
}


def _merge(base, extra):
    """Deep-merge `extra` over `base`; missing keys keep their defaults."""
    out = dict(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | None = None) -> dict:
    path = path or CONFIG_PATH
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"ERROR: config file not found at {path}\n"
              f"(set JOB_CONFIG to point at your config.toml)", file=sys.stderr)
        raise SystemExit(2)
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        print(f"ERROR: could not parse {path}: {e}", file=sys.stderr)
        raise SystemExit(2)
    return _merge(DEFAULTS, raw)


CFG = load_config()

# -- profile -----------------------------------------------------------
RESUME_PDF = os.path.join(_SCRIPT_DIR, CFG["profile"]["resume_pdf"]) \
    if not os.path.isabs(CFG["profile"]["resume_pdf"]) else CFG["profile"]["resume_pdf"]
PROFILE_NAME = CFG["profile"].get("name", "")
PROFILE_HEADLINE = CFG["profile"].get("headline", "")
PROFILE_SUMMARY = CFG["profile"].get("summary", "")

# -- filters -----------------------------------------------------------

def _pattern(section: dict, base: str) -> str:
    """Keyword lists (friendlier to edit) override the raw regex when non-empty."""
    kws = section.get(f"{base}_keywords") or []
    words = [re.escape(k.strip()) for k in kws if k.strip()]
    if words:
        return r"\b(" + "|".join(words) + r")\b"
    return section.get(f"{base}_regex") or ""


_F = CFG["filters"]
ROLE_REGEX = re.compile(_pattern(_F, "role_include"), re.I)
EXCLUDE_ROLE_REGEX = re.compile(_pattern(_F, "role_exclude"), re.I)
LOCATION_REGEX = re.compile(_pattern(_F, "location_include"), re.I)
EXCLUDE_LOC_REGEX = re.compile(_F.get("location_exclude_regex") or r"$^", re.I)
MAX_YOE = int(_F.get("max_years_experience", 2))

STATED_YOE_REGEX = re.compile(
    r"\b(\d{1,2})\s*(?:\+|plus)?\s*(?:to\s*|-|–)?\s*\d{0,2}\s*(?:years?|yrs?)\b",
    re.I,
)

TIER_KEYWORDS = [tuple(str(kw).lower() for kw in tier)
                 for tier in _F.get("location_priority_tiers", []) if tier]

# -- companies ---------------------------------------------------------
_CO = CFG["boards"].get("companies", {}) or {}
KEEP_COMPANIES = {str(c).strip().lower() for c in (_CO.get("keep") or []) if str(c).strip()}
DROP_COMPANIES = {str(c).strip().lower() for c in (_CO.get("drop") or []) if str(c).strip()}

# -- run ---------------------------------------------------------------
_RUN = CFG["run"]
DEDUP = bool(_RUN.get("dedup", True))
MAX_WORKERS = int(_RUN.get("max_workers", 40))
TIMEOUT = int(_RUN.get("timeout_seconds", 15))
WEB_PORT = int(os.environ.get("WEB_PORT") or _RUN.get("web_port", 8000))
CACHE_TTL_SECONDS = int(_RUN.get("cache_ttl_seconds", 600))
# Web-mode cache snapshot, resolved relative to the repo root.
SNAPSHOT_PATH = _RUN.get("snapshot_path") or ""
SNAPSHOT_PATH = os.path.join(_SCRIPT_DIR, SNAPSHOT_PATH) \
    if SNAPSHOT_PATH and not os.path.isabs(SNAPSHOT_PATH) \
    else (SNAPSHOT_PATH or "")
LIVE_FEED_PATH_CFG = str(_RUN.get("live_feed_path", "") or "")
PREVIEW_COUNT = int(_RUN.get("preview_count", 20))

# -- enrich (optional Gemini Flash-Lite JD annotation) -------------------
# OFF unless an API key resolves (see _resolve_enrich_key). The key is
# never committed: config.toml ships to the public repo, so the key lives
# in the env var, in a gitignored .env file, or (worst, warned) inline.
def _resolve_enrich_key():
    """API key resolution order: env GEMINI_API_KEY > [enrich].key (loud
    public-file warning) > [enrich].key_file (.env) contents."""
    env = os.environ.get("GEMINI_API_KEY", "").strip()
    if env:
        return env
    # Inline TOML key: supported for local testing, but config.toml is
    # committed — one scrub-less push would leak the key publicly.
    inline = str(CFG["enrich"].get("key", "") or "").strip()
    if inline:
        print("WARNING: [enrich].key stores an API key inside config.toml, "
              "which IS committed. Remove it before pushing — the safe "
              "places are the GEMINI_API_KEY env var or the gitignored "
              ".env file ([enrich].key_file).", file=sys.stderr)
        return inline
    key_file = str(CFG["enrich"].get("key_file", "") or "").strip()
    if key_file:
        path = key_file if os.path.isabs(key_file) \
            else os.path.join(_SCRIPT_DIR, key_file)
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError:
            return ""
        key = ""
        bare = []  # .env layouts that just hold the key with no KEY= line
        for ln in lines:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            if "=" in ln:
                k, v = ln.split("=", 1)
                if k.strip().upper() == "GEMINI_API_KEY":
                    key = v.strip().strip('"').strip("'").strip()
                    break
            else:
                bare.append(ln)
        if not key and bare:
            key = bare[0].strip().strip('"').strip("'")
        if key:
            if shutil.which("git"):
                ignored = subprocess.run(
                    ["git", "check-ignore", "-q", path], cwd=_SCRIPT_DIR,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                ).returncode == 0
                if not ignored:
                    print(f"WARNING: [enrich].key_file {path} is NOT "
                          "git-ignored — the key inside it would be "
                          "committed. Move it into data/ etc.", file=sys.stderr)
            return key
    return ""


ENRICH_API_KEY = _resolve_enrich_key()
ENRICH_MODEL = str(CFG["enrich"].get("model", "gemini-2.5-flash-lite")).strip() \
    .replace("/", "")
ENRICH_MAX_JOBS = int(CFG["enrich"].get("max_jobs", 60))
ENRICH_CONCURRENCY = int(CFG["enrich"].get("concurrency", 5))
ENRICH_TIMEOUT = int(CFG["enrich"].get("timeout_seconds", 25))
ENRICH_MAX_DESC_CHARS = int(CFG["enrich"].get("max_desc_chars", 6000))


def stated_max_years(text: str):
    """Highest lower-bound year figure mentioned in a job description."""
    nums = [int(m.group(1)) for m in STATED_YOE_REGEX.finditer(text or "")]
    return max(nums) if nums else None


def description_text(*fragments: str) -> str:
    """Concatenate description fragments and strip HTML tags/entities."""
    raw = " ".join(f for f in fragments if f)
    return re.sub(r"<[^>]+>", " ", html.unescape(raw))


def title_ok(title: str) -> bool:
    """Role-type filter: must match role_include and not role_exclude."""
    return bool(ROLE_REGEX.search(title)) and not EXCLUDE_ROLE_REGEX.search(title)


def location_ok(loc: str) -> bool:
    """Location filter: must match location_include and not location_exclude."""
    return bool(LOCATION_REGEX.search(loc or "")) and not EXCLUDE_LOC_REGEX.search(loc or "")


def yoe_ok(desc: str) -> bool:
    """Strict experience filter: stated maximum must not exceed MAX_YOE."""
    n = stated_max_years(desc)
    return n is None or n <= MAX_YOE


def company_allowed(name: str) -> bool:
    """Company allow-list/deny-list, matched case-insensitively."""
    n = (name or "").strip().lower()
    if not n:
        return True
    if n in DROP_COMPANIES:
        return False
    if KEEP_COMPANIES and n not in KEEP_COMPANIES:
        return False
    return True


def tier_of(loc: str) -> int:
    """Sort-priority tier from config [filters].location_priority_tiers."""
    l = (loc or "").lower()
    for t, kws in enumerate(TIER_KEYWORDS):
        if any(kw in l for kw in kws):
            return t
    return len(TIER_KEYWORDS)
