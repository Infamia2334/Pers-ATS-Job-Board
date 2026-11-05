"""Background-cached web server for the clickable UI.

Scrapes only on demand: with no snapshot the server pre-scrapes once at
startup (so the first click isn't a ~1 min block); with one it serves the
last scrape instantly and re-scrapes in the background when the ~cache_ttl
(default 10 min) expires or the Refresh button forces it. The snapshot at
[run].snapshot_path survives restarts. Lever is slow server-side (10-40 s
on big boards like palantir) — this cache is what hides that.
"""

import html
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import (CACHE_TTL_SECONDS, CONFIG_PATH, PROFILE_HEADLINE,
                     PROFILE_SUMMARY, SNAPSHOT_PATH, WEB_PORT)
from .engine import collect_jobs
from .page import WEB_PAGE


def _save_snapshot(jobs: list, ts: float, stamp: str):
    """Persist the last completed scrape (worker thread only, ~100 KB).

    Atomic replace so a crash mid-write can never leave a truncated file;
    failure is non-fatal — the cache just stays memory-only until restart.
    """
    if not SNAPSHOT_PATH:
        return
    try:
        os.makedirs(os.path.dirname(SNAPSHOT_PATH) or ".", exist_ok=True)
        tmp = SNAPSHOT_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"ts": ts, "stamp": stamp, "jobs": jobs}, f)
        os.replace(tmp, SNAPSHOT_PATH)
    except OSError as e:
        print(f"snapshot write failed ({e}); cache stays memory-only", flush=True)


def _load_snapshot():
    """Return (jobs, ts, stamp) from the last scrape, or None if unusable."""
    try:
        with open(SNAPSHOT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        jobs, ts = data["jobs"], float(data["ts"])
        if isinstance(jobs, list) and ts > 0:
            return jobs, ts, str(data.get("stamp", ""))
    except Exception:
        pass
    return None


def run_web():
    """Serve the clickable UI on http://localhost:<run.web_port>."""
    port = WEB_PORT
    page = (WEB_PAGE
            .replace("__HEADLINE__", html.escape(PROFILE_HEADLINE))
            .replace("__PROFILE_SUMMARY__", html.escape(PROFILE_SUMMARY)))

    state = {"jobs": None, "ts": 0.0, "stamp": "", "running": False}
    state_lock = threading.Lock()
    worker_lock = threading.Lock()  # prevents overlapping scrapes

    def refresh():
        with worker_lock:
            with state_lock:
                state["running"] = True
            jobs = collect_jobs()
            with state_lock:
                state["jobs"] = jobs
                state["ts"] = time.time()
                state["stamp"] = time.strftime("%H:%M", time.localtime())
                state["running"] = False
                _save_snapshot(jobs, state["ts"], state["stamp"])

    # Restart persistence: if the previous run left a snapshot, serve it
    # instantly and scrape only on demand (stale page load or the Refresh
    # button). Without one, pre-scrape at startup so the first click isn't
    # a ~1 min block — that startup scrape only happens on a cold start.
    snap = _load_snapshot()
    first_scrape = None
    if snap:
        with state_lock:
            state["jobs"], state["ts"], state["stamp"] = snap
    else:
        first_scrape = threading.Thread(target=refresh, daemon=True)
        first_scrape.start()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, ctype, payload):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path.startswith("/jobs"):
                try:
                    # ?refresh=1 is the explicit-demand path (Refresh button):
                    # always kick a re-scrape, regardless of cache age. Page
                    # loads / first clicks take the cache-first path and only
                    # re-scrape when the TTL expired — never a timer.
                    forced = "refresh=1" in self.path.partition("?")[2].split("&")
                    with state_lock:
                        jobs = state["jobs"]
                        stamp = state["stamp"]
                        running = state["running"]
                        fresh = (jobs is not None
                                 and (time.time() - state["ts"]) < CACHE_TTL_SECONDS)
                    if jobs is None and first_scrape is not None:
                        first_scrape.join()  # very first click: wait for warm-up
                        with state_lock:
                            jobs, stamp = state["jobs"], state["stamp"]
                            fresh, running = True, False
                    else:
                        kick = (forced and not running) \
                            or (not forced and not fresh and not running)
                        if kick:
                            # Flag first, spawn second: a poll landing between
                            # the two must still see running=True, or it would
                            # stop early and show the old snapshot forever.
                            with state_lock:
                                state["running"] = True
                            threading.Thread(target=refresh, daemon=True).start()
                            running = True
                    # A forced re-scrape must report refreshing even on a cache
                    # that is still TTL-fresh — otherwise the UI's poll stops
                    # early and only shows the old snapshot forever.
                    refreshing = (not fresh) or running
                    body = json.dumps({
                        "jobs": jobs or [],
                        "generated_at": stamp,
                        "cache_ttl_minutes": round(CACHE_TTL_SECONDS / 60),
                        "refreshing": refreshing,
                    }).encode()
                    self._send(200, "application/json; charset=utf-8", body)
                except Exception as e:
                    self._send(500, "application/json", json.dumps({"error": str(e)}).encode())
            elif self.path.startswith("/"):
                self._send(200, "text/html; charset=utf-8", page.encode())
            else:
                self._send(404, "text/plain", b"not found")

        def log_message(self, *args):
            pass

    print(f"Config: {CONFIG_PATH}")
    print(f"Serving the openings UI at http://localhost:{port} — Ctrl-C to stop.")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
