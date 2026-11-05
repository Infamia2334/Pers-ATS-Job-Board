"""Background-cached web server for the clickable UI.

Scrapes in a daemon thread at startup so button clicks are instant
afterwards; a ~cache_ttl (default 10 min) stale cache triggers a silent
background refresh while the previous results are served. Lever is slow
server-side (10-40 s on big boards like palantir) — this cache is what
hides that.
"""

import html
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import (CACHE_TTL_SECONDS, CONFIG_PATH, PROFILE_HEADLINE,
                     PROFILE_SUMMARY, WEB_PORT)
from .engine import collect_jobs
from .page import WEB_PAGE


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

    # Warm the cache at startup so button clicks are instant afterwards.
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
                    with state_lock:
                        jobs = state["jobs"]
                        stamp = state["stamp"]
                        running = state["running"]
                        fresh = (jobs is not None
                                 and (time.time() - state["ts"]) < CACHE_TTL_SECONDS)
                    if jobs is None:
                        first_scrape.join()  # very first click: wait for warm-up
                        with state_lock:
                            jobs, stamp, fresh, running = state["jobs"], state["stamp"], True, False
                    elif not fresh and not running:
                        # Stale cache: serve the old snapshot instantly and
                        # re-scrape in the background; the UI polls until the
                        # fresh run lands (frontend "refreshing" indicator).
                        threading.Thread(target=refresh, daemon=True).start()
                    body = json.dumps({
                        "jobs": jobs or [],
                        "generated_at": stamp,
                        "cache_ttl_minutes": round(CACHE_TTL_SECONDS / 60),
                        "refreshing": not fresh,
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
