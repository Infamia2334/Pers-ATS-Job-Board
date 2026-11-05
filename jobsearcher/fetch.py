"""HTTP plumbing shared by every source.

All networking in the package goes through fetch_json / fetch_text. Both
ask for gzip (urllib does not decompress itself; Greenhouse content boards
ship 10-30 MB raw vs ~1 MB gzipped) and callers fail silently on errors,
so a single dead endpoint never kills a run.
"""

import gzip
import json
import urllib.request

from .config import TIMEOUT


def fetch_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json",
            # Ask for gzip — the ATS boards send 10-30 MB of raw JSON for
            # content-bearing boards otherwise, and urllib does not unzip it.
            "Accept-Encoding": "gzip",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding", "") == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8", errors="ignore"))


def fetch_text(url: str) -> str:
    """Same as fetch_json but returns the decoded body as text (HTML feeds)."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Encoding": "gzip",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding", "") == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="ignore")
