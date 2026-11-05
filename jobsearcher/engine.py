"""Run every enabled source concurrently and assemble the tier-sorted feed."""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import CFG, DEDUP, MAX_WORKERS, company_allowed, tier_of
from .sources import (check_ashby, check_greenhouse, check_lever,
                      check_ycombinator, check_hn_whoishiring, check_remoteok,
                      check_weworkremotely, check_linkedin, check_zohorecruit,
                      _zoho_site_entries)


def _norm(text) -> str:
    """Whitespace-collapsed, case-folded text for dedup keys."""
    return re.sub(r"\s+", " ", str(text or "")).lower().strip()


def dedup_rows(rows: list) -> tuple:
    """Drop overlapping postings; returns (kept, dropped_count).

    Two keys: the apply URL (catches same posting regardless of how its
    title/fields differ), and (ATS, company, title, location) — which
    collapses identical listings that arrive twice via different links,
    e.g. the heavily overlapping WWR category feeds. A shared title at a
    *different* location survives: those are separate requisitions with
    separate apply links.
    """
    kept, seen_urls, seen_exact = [], set(), set()
    for row in rows:
        url = str(row.get("Direct_Apply_URL") or "").strip().rstrip("/")
        exact = (row["ATS"], _norm(row["Company"]), _norm(row["Title"]),
                 _norm(row["Location"]))
        if url and url in seen_urls:
            continue
        if exact in seen_exact:
            continue
        seen_exact.add(exact)
        if url:
            seen_urls.add(url)
        kept.append(row)
    return kept, len(rows) - len(kept)


def collect_jobs():
    """Fetch every enabled source and return the matching rows, tier-sorted."""
    ats_boards = CFG["boards"]
    all_jobs = []
    tasks = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        if ats_boards["ashby"].get("enabled"):
            for s in ats_boards["ashby"].get("boards", []):
                tasks.append(ex.submit(check_ashby, s))
        if ats_boards["greenhouse"].get("enabled"):
            for s in ats_boards["greenhouse"].get("boards", []):
                tasks.append(ex.submit(check_greenhouse, s))
        if ats_boards["lever"].get("enabled"):
            for s in ats_boards["lever"].get("boards", []):
                tasks.append(ex.submit(check_lever, s))
        tasks.append(ex.submit(check_ycombinator))
        tasks.append(ex.submit(check_hn_whoishiring))
        tasks.append(ex.submit(check_remoteok))
        tasks.append(ex.submit(check_linkedin))
        for feed in CFG["feeds"]["weworkremotely"].get("feeds", []):
            tasks.append(ex.submit(check_weworkremotely, feed))
        for site_cfg in _zoho_site_entries():
            tasks.append(ex.submit(check_zohorecruit, site_cfg))
        for fut in as_completed(tasks):
            for row in fut.result():
                if company_allowed(row["Company"]):
                    row["Tier"] = tier_of(row["Location"])
                    all_jobs.append(row)

    if DEDUP:
        all_jobs, _ = dedup_rows(all_jobs)

    all_jobs.sort(key=lambda j: (j["Tier"], j["Company"], j["Title"]))
    return all_jobs
