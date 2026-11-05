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
