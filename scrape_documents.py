"""Milestone 3 — Document ingestion (scraping).

Downloads the sources listed in planning.md → Documents and saves each as a
plain-text file in ``documents/``, ready for ``chunk_documents.py`` to clean
and chunk.

Two source types are handled:
  * Reddit threads — fetched via Reddit's ``.json`` endpoint and flattened into
    the post body plus its comments (more reliable than scraping Reddit HTML).
  * Blogs / news pages — fetched as HTML and reduced to visible text with the
    standard-library HTML parser (no BeautifulSoup dependency).

This is a library of functions; ``main()`` just wires them together so the file
can also be run directly:

    python scrape_documents.py
    python scrape_documents.py --output documents
"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import requests

# --- Sources (planning.md → Documents) ---------------------------------------
DOCUMENT_URLS: list[str] = [
    "https://www.reddit.com/r/newhaven/comments/1n9mjbn/back_in_new_haven_recommend_me_a_new_high_quality/",
    "https://www.theadventuristmagazine.com/city-guides/northeast/connecticut/new-haven-best-restaurants",
    "https://admissions.yale.edu/posts/2020-10-20-a-new-haven-eating-guide-certified-by-an-aspiring-foodie",
    "https://www.infonewhaven.com/who-knew-blog/new-haven-restaurants-lead-connecticut-magazines-top-new-restaurants-for-2026-list/",
    "https://www.reddit.com/r/newhaven/comments/1q12va0/ive_compiled_a_list_of_food_places_in_new_haven/",
    "https://www.reddit.com/r/newhaven/comments/16h68pe/new_haven_locals_where_should_i_eat_tonight/",
]

# A browser-like UA — Reddit and many CDNs reject the default requests UA.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
TIMEOUT = 30  # seconds
MIN_TEXT_LEN = 200  # below this, treat extraction as failed and try the archive
WAYBACK_API = "http://archive.org/wayback/available"


# --- HTTP --------------------------------------------------------------------
def fetch(url: str, *, as_json: bool = False):
    """GET ``url`` with a browser-like User-Agent. Returns text, or parsed JSON."""
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json() if as_json else resp.text


# --- Reddit ------------------------------------------------------------------
def is_reddit_url(url: str) -> bool:
    return "reddit.com" in urlparse(url).netloc


def _walk_comments(children: list, out: list[str], depth: int = 0) -> None:
    """Depth-first collect comment bodies from a Reddit listing's children."""
    for child in children:
        if child.get("kind") != "t1":
            continue  # skip "more comments" stubs and non-comment nodes
        data = child.get("data", {})
        body = (data.get("body") or "").strip()
        if body and body not in ("[deleted]", "[removed]"):
            out.append(("  " * depth) + body)
        replies = data.get("replies")
        if isinstance(replies, dict):
            _walk_comments(replies.get("data", {}).get("children", []), out, depth + 1)


def scrape_reddit(url: str) -> str:
    """Fetch a Reddit thread as text: title, post body, then all comments."""
    json_url = url.rstrip("/") + "/.json"
    listings = fetch(json_url, as_json=True)

    post = listings[0]["data"]["children"][0]["data"]
    parts: list[str] = [post.get("title", "").strip()]
    selftext = (post.get("selftext") or "").strip()
    if selftext:
        parts.append(selftext)

    comments: list[str] = []
    if len(listings) > 1:
        _walk_comments(listings[1]["data"]["children"], comments)
    if comments:
        parts.append("\n--- Comments ---\n")
        parts.extend(comments)

    return "\n\n".join(p for p in parts if p)


# --- Generic HTML ------------------------------------------------------------
class _TextExtractor(HTMLParser):
    """Collect visible text, dropping scripts/styles/nav and adding line breaks."""

    _SKIP = {"script", "style", "noscript", "head", "nav", "header", "footer", "svg", "form"}
    _BLOCK = {
        "p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
        "section", "article", "ul", "ol", "blockquote", "table",
    }

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_data(self, data):
        if self._skip_depth == 0 and data.strip():
            self._chunks.append(data)

    def get_text(self) -> str:
        text = "".join(self._chunks)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n\s*", "\n\n", text)  # collapse blank-line runs
        return text.strip()


def extract_text_from_html(html: str) -> str:
    """Reduce an HTML document to readable visible text."""
    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()


def scrape_webpage(url: str) -> str:
    """Fetch a non-Reddit page and return its visible text."""
    return extract_text_from_html(fetch(url))


# --- Internet Archive fallback ----------------------------------------------
def wayback_snapshot_url(url: str) -> str | None:
    """Return a raw (toolbar-free) Wayback snapshot URL for ``url``, or None."""
    data = fetch(WAYBACK_API + f"?url={url}", as_json=True)
    snap = data.get("archived_snapshots", {}).get("closest", {})
    if snap.get("available"):
        # The ``id_`` suffix returns the originally archived bytes, no IA chrome.
        return f"http://web.archive.org/web/{snap['timestamp']}id_/{url}"
    return None


def scrape_via_wayback(url: str) -> str:
    """Recover a page's text from the Internet Archive when the live site blocks us."""
    snap = wayback_snapshot_url(url)
    return extract_text_from_html(fetch(snap)) if snap else ""


def scrape_url(url: str) -> str:
    """Scrape a URL, falling back to the Internet Archive if the live site blocks us.

    Reddit blocks unauthenticated bots and some blogs sit behind a WAF
    (e.g. Sucuri) that serves a JS challenge. In those cases we transparently
    retry against the page's archived snapshot. Raises if no usable text can be
    obtained from either source.
    """
    try:
        text = scrape_reddit(url) if is_reddit_url(url) else scrape_webpage(url)
    except Exception:
        text = ""

    if len(text.strip()) >= MIN_TEXT_LEN:
        return text

    archived = scrape_via_wayback(url)
    if len(archived.strip()) >= MIN_TEXT_LEN:
        print("    (live site blocked — recovered from Internet Archive)")
        return archived

    raise RuntimeError(
        "blocked by the source and no usable Internet Archive snapshot exists — "
        "open the page and paste its text into a .txt file in documents/ "
        "(planning.md lists manual copying as a valid ingestion method)"
    )


# --- Saving ------------------------------------------------------------------
def filename_for_url(url: str, index: int) -> str:
    """Build a stable, readable .txt filename for a source URL."""
    parsed = urlparse(url)
    if is_reddit_url(url):
        # .../comments/<id>/<slug>/  → reddit_<slug-or-id>
        parts = [p for p in parsed.path.split("/") if p]
        slug = parts[-1] if parts and parts[-1] != "comments" else (parts[-2] if len(parts) > 1 else "post")
        stem = f"reddit_{slug}"
    else:
        domain = parsed.netloc.replace("www.", "").split(".")[0]
        slug = (parsed.path.rstrip("/").split("/") or ["page"])[-1] or "page"
        stem = f"{domain}_{slug}"
    stem = re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")[:60]
    return f"{index:02d}_{stem}.txt"


def save_document(text: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")


# --- Driver ------------------------------------------------------------------
def scrape_all(urls: list[str], output_dir: Path) -> list[Path]:
    """Scrape every URL and save it to output_dir. Returns the saved file paths."""
    saved: list[Path] = []
    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] {url}")
        try:
            text = scrape_url(url)
        except Exception as exc:  # keep going if one source fails
            print(f"    ! failed: {exc}", file=sys.stderr)
            continue
        if not text.strip():
            print("    ! no text extracted — skipped", file=sys.stderr)
            continue
        dest = output_dir / filename_for_url(url, i)
        save_document(text, dest)
        print(f"    saved {dest.name} ({len(text):,} chars)")
        saved.append(dest)
    return saved


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--output", type=Path, default=Path("documents"), help="where to save scraped text")
    args = parser.parse_args()

    saved = scrape_all(DOCUMENT_URLS, args.output)
    print(f"\nSaved {len(saved)}/{len(DOCUMENT_URLS)} sources to {args.output}/")
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
