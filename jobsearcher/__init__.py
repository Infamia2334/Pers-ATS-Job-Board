"""Job discovery engine — config-driven scraper and openings UI.

Modules:
  config   — config.toml loading (stdlib tomllib, Python 3.12+) and the
             compiled filter regexes / per-module constants
  fetch    — gzip-aware HTTP plumbing (fetch_json / fetch_text)
  sources  — one check_* function per ATS board or feed
  engine   — collect_jobs(): run every source concurrently, sort by tier
  page     — the single-page UI HTML
  web      — run_web(): background-cached HTTP server
  cli      — main() (CSV mode) and verify_boards() (liveness checking)

The `python3 discover_jobs.py` shim at the repo root dispatches
--web / --verify / CSV mode.
"""

from .config import (CFG, CONFIG_PATH, DEFAULTS, WEB_PORT, MAX_WORKERS,
                     TIMEOUT, CACHE_TTL_SECONDS, PREVIEW_COUNT, DEDUP,
                     RESUME_PDF, PROFILE_NAME, PROFILE_HEADLINE,
                     PROFILE_SUMMARY, MAX_YOE, KEEP_COMPANIES,
                     DROP_COMPANIES, load_config, stated_max_years,
                     description_text, title_ok, location_ok, yoe_ok,
                     company_allowed, tier_of)

__all__ = [
    "CFG", "CONFIG_PATH", "DEFAULTS", "WEB_PORT", "MAX_WORKERS", "TIMEOUT",
    "CACHE_TTL_SECONDS", "PREVIEW_COUNT", "DEDUP", "RESUME_PDF", "PROFILE_NAME",
    "PROFILE_HEADLINE", "PROFILE_SUMMARY", "MAX_YOE", "KEEP_COMPANIES",
    "DROP_COMPANIES", "load_config", "stated_max_years", "description_text",
    "title_ok", "location_ok", "yoe_ok", "company_allowed", "tier_of",
]
