"""Source checkers: one function per job board or feed.

Every `check_*` fetches one public endpoint and returns a list of
normalized rows (see `_row`). Failures are swallowed (`except Exception`),
so a single dead board or rate-limited feed never kills a run —
`jobsearcher.cli.verify_boards` is the loud path for finding dead slugs.

Company/location field shapes differ per ATS: Greenhouse nests location
under `location.name` and must be fetched with `?content=true` or the
description (and therefore the YOE filter) silently disappears; Lever
locations sit under `categories.location` with `workplaceType`, and its
descriptions come in the plain `?mode=json` payload; Ashby has a separate
`isRemote` flag and takes an `/application` suffix on its apply links.
"""

import html
import json
import re
import urllib.parse
import xml.etree.ElementTree

from .fetch import fetch_json, fetch_text
from .config import (CFG, RESUME_PDF, ROLE_REGEX, EXCLUDE_ROLE_REGEX,
                     LOCATION_REGEX, EXCLUDE_LOC_REGEX,
                     title_ok, location_ok, yoe_ok,
                     stated_max_years, description_text)


_AI_RE = re.compile(
    r"\b(ai|llm|agent|agentic|rag|eval|evals|voice|ml|machine learning|"
    r"genai|inference|langchain|langfuse|vector|embedding|prompt)\b",
    re.I,
)
_STARTUP_SOURCES = {"Ashby", "YC", "HN"}
_AI_COMPANIES = {
    "cardboard", "composio", "sarvam", "perplexity", "elevenlabs", "deepgram",
    "retell-ai", "vapi", "bland", "browserbase", "e2b", "exa", "mem0",
    "braintrust", "ema", "sierra", "decagon", "harvey", "weaviate", "mastra",
    "cerebras", "lambda", "runpod", "cohere", "openrouter", "cursor",
    "primeintellect", "pinecone", "factory", "cognition", "baseten",
    "fireworks", "modal", "yellow.ai",
}


def recommend_pdf(ats: str, company: str, title: str, desc: str = "") -> str:
    """Route each role to the right tailored resume variant (Archetype A/B × Startup/BGV)."""
    co_lower = (company or "").strip().lower()
    is_ai = bool(_AI_RE.search(f"{title} {company}")) or co_lower in _AI_COMPANIES
    is_startup = ats in _STARTUP_SOURCES
    if is_ai and is_startup:
        return "SE__AI_Backend (Startups).pdf"
    if is_ai and not is_startup:
        return "SE__AI_Backend (BGV).pdf"
    if is_startup:
        return "SE__Backend (Startups).pdf"
    return "SE__Backend (BGV).pdf"


def _row(ats: str, company: str, title: str, loc: str, stated_yoe, url: str,
         desc: str = "") -> dict:
    """Normalized row shape shared by every source.

    `desc` is internal plumbing for the optional AI annotation layer
    (engine passes it to enrich, then strips the key before any row
    escapes into the CSV/snapshot). An empty/absent desc — YC and
    LinkedIn guest cards — simply leaves the key off the row.
    """
    row = {
        "ATS": ats,
        "Company": company,
        "Title": title,
        "Location": loc,
        "Max_Stated_YOE": stated_yoe if stated_yoe is not None else "n/a",
        "Recommended_PDF": recommend_pdf(ats, company, title, desc),
        "Direct_Apply_URL": url,
    }
    if desc:
        row["_desc"] = desc
    return row


def check_ashby(slug: str):
    results = []
    try:
        data = fetch_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        for j in data.get("jobs", []):
            title = j.get("title", "")
            loc = j.get("location", "") or ""
            is_remote = j.get("isRemote", False)
            loc_str = f"{loc} (Remote)" if is_remote and "remote" not in loc.lower() else loc
            if not title_ok(title) or not location_ok(loc_str):
                continue
            desc = description_text(j.get("descriptionPlain") or "",
                                    j.get("descriptionHtml") or "")
            stated_yoe = stated_max_years(desc)
            if not yoe_ok(desc):
                continue
            url = j.get("jobUrl") or f"https://jobs.ashbyhq.com/{slug}/{j.get('id')}"
            results.append(_row("Ashby", slug.title(), title, loc_str, stated_yoe,
                                url.rstrip("/") + "/application", desc))
    except Exception:
        pass
    return results


def check_greenhouse(slug: str):
    results = []
    try:
        # ?content=true is required or the description is absent and the YOE
        # filter silently stops applying.
        data = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
        for j in data.get("jobs", []):
            title = j.get("title", "")
            loc = (j.get("location") or {}).get("name", "")
            if not title_ok(title) or not location_ok(loc):
                continue
            desc = description_text(j.get("content") or "")
            stated_yoe = stated_max_years(desc)
            if not yoe_ok(desc):
                continue
            url = j.get("absolute_url", "")
            results.append(_row("Greenhouse", slug.title(), title, loc, stated_yoe, url,
                                desc))
    except Exception:
        pass
    return results


def check_lever(slug: str):
    results = []
    try:
        data = fetch_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
        if not isinstance(data, list):
            return results
        for j in data:
            title = j.get("text", "")
            cats = j.get("categories") or {}
            loc = cats.get("location", "") or ""
            if not loc and isinstance(cats.get("allLocations"), list) and cats["allLocations"]:
                loc = cats["allLocations"][0]
            workplace = j.get("workplaceType", "")
            loc_str = f"{loc} ({workplace})" if workplace else str(loc)
            if not title_ok(title) or not location_ok(loc_str):
                continue
            list_texts = [li.get("content", "") for li in (j.get("lists") or [])]
            desc = description_text(j.get("descriptionPlain") or "", *list_texts)
            stated_yoe = stated_max_years(desc)
            if not yoe_ok(desc):
                continue
            url = j.get("applyUrl") or j.get("hostedUrl", "")
            results.append(_row("Lever", slug.title(), title, loc_str, stated_yoe, url,
                                desc))
    except Exception:
        pass
    return results


# ---------------- Non-ATS sources (all fail silently) ----------------

def check_ycombinator():
    """One public guest fetch of YC Work at a Startup eng listings.

    Guest access serves a fixed curated sample (~30 recently-active eng
    jobs) of the full 2900+ listing board; no description text is exposed,
    so the YOE filter cannot apply here (rows show n/a). Filters and
    pagination on the page are client-side Inertia and are ignored."""
    if not CFG["feeds"]["yc"].get("enabled"):
        return []
    results = []
    try:
        page = fetch_text("https://www.workatastartup.com/jobs?roles=eng")
        blob = re.search(r'data-page="([^"]+)"', page)
        if not blob:
            return results
        props = json.loads(html.unescape(blob.group(1))).get("props", {})
    except Exception:
        return results
    for j in props.get("jobs", []):
        title = j.get("title", "")
        loc = j.get("location", "") or ""
        if not title_ok(title) or not location_ok(loc):
            continue
        slug = j.get("companySlug") or ""
        if slug and j.get("id"):
            url = f"https://www.workatastartup.com/companies/{slug}/jobs/{j['id']}"
        else:
            url = j.get("applyUrl", "")
        results.append(_row("YC", j.get("companyName") or "YC startup", title,
                            loc, None, url))
    return results


# Region keywords used by the HN "Remote (US)" window check. Kept here rather
# than in config because it only matters for free-form HN posts; it mirrors
# location_include_regex minus `remote`/`global`/`anywhere`.
_HN_ALLOWED_REGIONS = re.compile(
    r"\b(europe|emea|germany|netherlands|amsterdam|berlin|munich|uk|london|"
    r"estonia|tallinn|dublin|ireland|stockholm|sweden|singapore|japan|tokyo|"
    r"apac|india|bengaluru|global|worldwide)\b", re.I)


def check_hn_whoishiring():
    """Monthly 'Ask HN: Who is hiring?' thread via the public Algolia API.

    Seed-stage heavy. Company/title come from the post's opening line and
    the YOE filter runs on the full post text."""
    if not CFG["feeds"]["hn"].get("enabled"):
        return []
    results = []
    try:
        stories = fetch_json(
            f"https://hn.algolia.com/api/v1/search_by_date"
            f"?query=%22Who%20is%20hiring%22&tags=story,author_whoishiring&hitsPerPage=10"
        )
        hits = stories.get("hits", [])
        if not hits:
            return results
        latest = max(hits, key=lambda h: h.get("created_at", ""))
        thread = fetch_json(
            f"https://hn.algolia.com/api/v1/search_by_date"
            f"?tags=comment,story_{latest['objectID']}&hitsPerPage=1000"
        )
    except Exception:
        return results
    for c in thread.get("hits", []):
        raw = c.get("comment_text") or ""
        try:
            first_link = html.unescape(re.search(r'<a\s+href="([^"]+)"', raw).group(1))
            first_link = re.sub(r"[\),\.]+$", "", first_link)
        except AttributeError:
            first_link = None
        text = re.sub(r"\s+", " ", description_text(raw)).strip()
        if not text or not ROLE_REGEX.search(text):
            continue
        # Structured posts look like "Company | Role | Location"; prefer that,
        # falling back to the opening 150 chars for freer-form posts. Skip
        # segments that are bare links, "Remote …", or a salary figure — some
        # posts put those before the actual role name.
        parts = [p.strip() for p in text.split(" | ")]
        candidate = next((p for p in parts[1:4]
                          if not re.match(r"^https?://", p)
                          and not re.match(r"^remote\b", p, re.I)
                          and "$" not in p[:24]), None)
        if len(parts) >= 2 and candidate:
            title = candidate
            exclude_scope = candidate + " " + " ".join(parts[3:5])[:120]
        else:
            title = parts[0]
            exclude_scope = text[:150]
        if EXCLUDE_ROLE_REGEX.search(exclude_scope):
            continue
        # Forget links (and parenthetical URLs) when naming the company, and
        # prefer the segment before " - " (posts like "DuckDuckGo - we are
        # looking for candidates that ..." name the company first).
        company = re.split(r"\bhttps?:", parts[0])[0].split("(")[0].strip()
        company = re.split(r"\s+[-–—]\s+", company)[0]
        company = re.sub(r"^\W+|\W+$", "", company)
        company = company[:60] if len(company) > 3 or not company else "HN poster"
        # Some posters open with plain metadata ("Location: X Remote: Yes …",
        # "Position: …") instead of a company name; no usable Company/Title
        # can be parsed from those, so drop the post outright.
        if re.match(r"^(?:location|remote|position|title|salary|apply|experience)\s*:",
                    company, re.I) \
           or re.match(r"^(?:location|remote|position|title|salary|apply|experience)\s*:",
                       title, re.I):
            continue
        lm = LOCATION_REGEX.search(text)
        if not lm or EXCLUDE_LOC_REGEX.search(text):
            continue
        # "Remote" posts that are remote-US-only: check a window around the
        # location mention for US/Canada markers, unless an explicitly allowed
        # country/region is named in the same window (e.g. "North America AND
        # Europe", "US OR EU" — those stay).
        window = text[max(0, lm.start() - 80):lm.end() + 80]
        if re.search(r"\b(u\.?s\.?\.?|usa|united states|north america|canada)\b", window, re.I) \
           and not _HN_ALLOWED_REGIONS.search(window):
            continue
        stated_yoe = stated_max_years(text)
        if not yoe_ok(text):
            continue
        results.append(_row("HN", company[:60] or "HN poster", title[:150],
                            lm.group(0), stated_yoe,
                            first_link or f"https://news.ycombinator.com/item?id={c.get('objectID')}",
                            text))
    return results


def check_remoteok():
    """https://remoteok.com/api — recent 100 remote postings with descriptions."""
    if not CFG["feeds"]["remoteok"].get("enabled"):
        return []
    results = []
    try:
        data = fetch_json("https://remoteok.com/api")
    except Exception:
        return results
    for j in data:
        if not isinstance(j, dict) or not j.get("position"):
            continue  # first element is the API's legal meta blob
        title = j.get("position", "")
        if not title_ok(title):
            continue
        loc = j.get("location") or ""
        if not loc.strip() or LOCATION_REGEX.search(loc) is None:
            if (loc or "").strip().lower() not in ("worldwide", "remote", "anywhere", "earth", ""):
                continue
            loc = "Remote (Global)"
        if EXCLUDE_LOC_REGEX.search(loc):
            continue
        desc = description_text(j.get("description") or "")
        stated_yoe = stated_max_years(desc)
        if not yoe_ok(desc):
            continue
        results.append(_row("RemoteOK", (j.get("company") or "RemoteOK company")[:60],
                            title[:150], loc, stated_yoe,
                            j.get("apply_url") or j.get("url", ""), desc))
    return results


def check_weworkremotely(feed: str):
    """WeWorkRemotely category RSS (full-stack & general programming)."""
    if not CFG["feeds"]["weworkremotely"].get("enabled"):
        return []
    results = []
    try:
        raw = fetch_text(f"https://weworkremotely.com/categories/{feed}.rss")
        root = xml.etree.ElementTree.fromstring(raw)
    except Exception:
        return results
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title_ok(title):
            continue
        lm = LOCATION_REGEX.search(title)
        # WWR items are all remote; the parenthetical usually narrows region.
        loc = lm.group(0) if lm else "Remote (Global)"
        if EXCLUDE_LOC_REGEX.search(title):
            continue
        desc = description_text(item.findtext("description") or "")
        stated_yoe = stated_max_years(desc)
        if not yoe_ok(desc):
            continue
        results.append(_row("WWR", re.split(r":\s*", title)[0][:60], title[:150],
                            loc, stated_yoe, link, desc))
    return results


def check_linkedin():
    """LinkedIn guest search cards. Rate-limited: expect 429s some runs.

    No description without a second request per job, so the YOE filter
    cannot apply and Max_Stated_YOE shows n/a for these rows. One request
    per query — per-job detail fetches would trip the limiter, so never
    add them."""
    if not CFG["feeds"]["linkedin"].get("enabled"):
        return []
    results = []
    for query_url in CFG["feeds"]["linkedin"].get("queries", []):
        try:
            frag = fetch_text(query_url)
        except Exception:
            continue  # 429/999 — skip this query quietly
        # Each card: <div class="base-card ... data-entity-urn="urn:li:jobPosting:<id>">
        for card in re.split(r'<div\s+class="base-card[^"]*"', frag)[1:]:
            jid = re.search(r'data-entity-urn="urn:li:jobPosting:(\d+)"', card)
            t = re.search(r'base-search-card__title[^>]*>\s*([^<]+?)\s*<', card)
            # company name sits in the subtitle (often wrapped in an <a>)
            s = re.search(r'base-search-card__subtitle[^>]*>\s*(?:<a[^>]*>)?\s*([^<]+?)\s*'
                          r'(?:</a>)?\s*<', card)
            l = re.search(r'job-search-card__location[^>]*>\s*([^<]+?)\s*<', card)
            if not (jid and t):
                continue
            company = html.unescape(s.group(1)).strip() if s else "LinkedIn posting"
            title = html.unescape(t.group(1)).strip()
            loc = html.unescape(l.group(1)).strip() if l else ""
            if not title_ok(title) or not location_ok(loc):
                continue
            results.append(_row("LinkedIn", company[:60], title[:150], loc, None,
                                f"https://www.linkedin.com/jobs/view/{jid.group(1)}"))
    return results


def _zoho_site_entries():
    """Parse feeds.zoho.sites entries of the form "company | site | page_name"."""
    out = []
    for raw in CFG["feeds"]["zoho"].get("sites", []):
        parts = [p.strip() for p in str(raw).split("|")]
        if len(parts) != 3 or not all(parts):
            raise ValueError(
                f"config feeds.zoho.sites entry {raw!r} must be 'company | site | page_name'")
        out.append({"company": parts[0], "site": parts[1], "page_name": parts[2]})
    return out


def check_zohorecruit(site_cfg: dict):
    """Zoho Recruit lister via the public endpoint embed_jobs.js queries."""
    if not CFG["feeds"]["zoho"].get("enabled"):
        return []
    results = []
    company = site_cfg["company"]
    site = site_cfg["site"].rstrip("/")
    try:
        data = fetch_json(
            f"{site}/recruit/v2/public/Job_Openings"
            f"?pagename={urllib.parse.quote(site_cfg['page_name'])}"
        )
    except Exception:
        return results
    if not isinstance(data, dict) or data.get("code") != "success":
        return results
    for j in data.get("data", []):
        title = (j.get("Posting_Title") or j.get("Job_Opening_Name") or "").strip()
        loc = ", ".join(x for x in (j.get("City"), j.get("State"), j.get("Country")) if x)
        if not title_ok(title):
            continue
        if not LOCATION_REGEX.search(loc or "remote") and not LOCATION_REGEX.search(title):
            continue
        if EXCLUDE_LOC_REGEX.search(loc):
            continue
        desc = description_text(j.get("Job_Description") or "")
        stated_yoe = stated_max_years(desc)
        if not yoe_ok(desc):
            continue
        results.append(_row("Zoho", company, title[:150], loc or "Remote (Global)",
                            stated_yoe, j.get("$url", ""), desc))
    return results
