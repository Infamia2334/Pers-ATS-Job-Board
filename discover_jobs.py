#!/usr/bin/env python3
"""
Automated Job Discovery Engine — thin launcher.

The implementation lives in the jobsearcher package (config, fetch,
sources, engine, page, web, cli). Its behaviour is entirely driven by
config.toml next to this file — profile, role/location filters, board
slugs, feed toggles, company keep/drop lists, thread counts, ports.

Run modes:
  python3 discover_jobs.py            # CSV mode: write Live_Openings_Feed.csv
  python3 discover_jobs.py --web      # serve the UI at localhost:<web_port>
  python3 discover_jobs.py --verify   # check board slugs / feeds are live
  ./start.sh                          # same as --web, plus start/stop/status

All fetches fail silently (except: pass) so a single dead endpoint never
kills a run; --verify is the loud path for finding dead slugs.
"""

import sys

import jobsearcher  # noqa: F401  (loads config; also makes d.CFG* lookups work)
from jobsearcher import (CFG, CONFIG_PATH, WEB_PORT, MAX_WORKERS,
                         RESUME_PDF)  # noqa: F401  (start.sh reads d.WEB_PORT)
from jobsearcher.cli import main, verify_boards
from jobsearcher.web import run_web

if __name__ == "__main__":
    if "--web" in sys.argv:
        run_web()
    elif "--verify" in sys.argv:
        verify_boards()
    else:
        main()
