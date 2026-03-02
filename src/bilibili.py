"""bilibili.py — Site-specific extractor for Bilibili articles.

Bilibili serves CAPTCHA pages to automated HTTP requests, so trafilatura
cannot extract content.  This module uses the public Bilibili API instead.

Supported URL patterns:
    - https://www.bilibili.com/read/cvNNNNNN   (article / 专栏)
    - https://b23.tv/xxxxx  (short links that redirect to the above)
"""

import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

from utils import clean_text

# Shared browser-like headers — Bilibili API returns -352 without these.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}

_TIMEOUT = 15  # seconds


# ── URL detection ──────────────────────────────────────────────────────

def is_bilibili_url(url: str) -> bool:
    """Return True if *url* points to a Bilibili page we can extract."""
    host = urlparse(url).netloc.lower()
    return host in ("www.bilibili.com", "bilibili.com", "b23.tv")


def resolve_short_url(url: str) -> str:
    """Follow redirects for short-link services (b23.tv, etc.).

    Returns the final URL after all redirects.
    """
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return resp.url  # type: ignore[return-value]


# ── HTML → plain text ──────────────────────────────────────────────────

class _HTMLToText(HTMLParser):
    """Minimal HTML-to-text converter for Bilibili article markup."""

    _BLOCK_TAGS = frozenset(("p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"))
    _SKIP_TAGS = frozenset(("figcaption", "style", "script"))

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        if tag == "p":
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def _html_to_text(html: str) -> str:
    """Strip HTML tags from Bilibili article content and return plain text."""
    parser = _HTMLToText()
    parser.feed(html)
    return parser.get_text()


# ── API extraction ─────────────────────────────────────────────────────

def _parse_article_id(url: str) -> int | None:
    """Extract the numeric article ID from a bilibili.com/read/cvNNN URL."""
    m = re.search(r"/read/cv(\d+)", url)
    return int(m.group(1)) if m else None


def _fetch_json(api_url: str) -> dict:
    """GET a Bilibili API endpoint and return the parsed JSON response."""
    req = urllib.request.Request(api_url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read())  # type: ignore[no-any-return]


def extract_bilibili(url: str) -> tuple[str, str | None]:
    """Extract article text and title from a Bilibili URL.

    Resolves short links, calls the Bilibili article API, converts HTML to
    plain text, and returns ``(text, title)``.

    Raises SystemExit on unrecoverable errors (matching the rest of the
    pipeline's error-handling style).
    """
    # Resolve short links (b23.tv → bilibili.com)
    parsed = urlparse(url)
    if parsed.netloc.lower() == "b23.tv":
        print(f"Resolving short link: {url}", file=sys.stderr)
        url = resolve_short_url(url)
        print(f"  → {url}", file=sys.stderr)

    article_id = _parse_article_id(url)
    if article_id is None:
        print(
            f"Error: Unsupported Bilibili URL format: {url}\n"
            "  Currently only article pages (/read/cvNNN) are supported.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Fetching Bilibili article cv{article_id} via API...", file=sys.stderr)
    data = _fetch_json(
        f"https://api.bilibili.com/x/article/view?id={article_id}&from=web"
    )

    if data.get("code") != 0:
        print(
            f"Error: Bilibili API returned code {data.get('code')}: "
            f"{data.get('message', 'unknown error')}",
            file=sys.stderr,
        )
        sys.exit(1)

    article = data["data"]
    title: str | None = article.get("title") or None
    content_html: str = article.get("content", "")

    if not content_html:
        print("Error: Bilibili article has no content.", file=sys.stderr)
        sys.exit(1)

    raw_text = _html_to_text(content_html)
    text = clean_text(raw_text)

    if not text:
        print("Error: Could not extract readable text from Bilibili article.", file=sys.stderr)
        sys.exit(1)

    word_count = len(text)  # character count is more meaningful for CJK
    print(f"Extracted {word_count} characters from: {title or '(untitled)'}", file=sys.stderr)
    return text, title
