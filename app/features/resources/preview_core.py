"""What a web address is about: page title, description and site name (PROJECT_BRIEF.md §2.4).

Run by the `resources.preview` job, never during a request. Only http and https, also
after redirects; at most 1 MB read, 10 s per request; only the page head is parsed, as
text. The result goes in `Resource.meta`, shown as a hint: the owner's title wins.

GitHub addresses are also read without the network: `owner/repo`, issue or PR number,
file path at a commit.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

MAX_BYTES = 1024 * 1024
TIMEOUT = 10
USER_AGENT = "Cairn/0.1 (link preview)"
_GITHUB = re.compile(
    r"^/(?P<owner>[A-Za-z0-9_.-]{1,39})/(?P<repo>[A-Za-z0-9_.-]{1,100})"
    r"(?:/(?P<section>issues|pull|discussions|blob|tree|commit|releases/tag)/(?P<rest>.+?))?/?$"
)


class PreviewError(Exception):
    pass


def github_ref(url: str) -> dict[str, Any] | None:
    """{"repo", "item", "number" | "ref" (+ "path")} for a github.com address, else None."""
    parts = urlsplit(url)
    if (parts.hostname or "").lower() not in ("github.com", "www.github.com"):
        return None
    match = _GITHUB.match(parts.path)
    if not match:
        return None
    ref: dict[str, Any] = {"repo": f"{match['owner']}/{match['repo']}", "item": "repository"}
    section, rest = match["section"], match["rest"]
    if section in ("issues", "pull", "discussions") and rest.split("/")[0].isdigit():
        ref["item"] = {"issues": "issue", "pull": "pull request", "discussions": "discussion"}[section]
        ref["number"] = int(rest.split("/")[0])
    elif section in ("blob", "tree"):
        commit, _, path = rest.partition("/")
        ref.update(item="file" if section == "blob" else "folder", ref=commit, path=path)
    elif section == "commit":
        ref.update(item="commit", ref=rest.split("/")[0])
    elif section == "releases/tag":
        ref.update(item="release", ref=rest)
    return ref


def github_title(ref: dict[str, Any]) -> str:
    """A readable default title from a GitHub reference: `owner/repo#12`, `repo: path`."""
    if "number" in ref:
        return f"{ref['repo']}#{ref['number']}"
    if ref.get("path"):
        return f"{ref['repo']}: {ref['path']}"
    if ref.get("ref"):
        return f"{ref['repo']} @ {ref['ref'][:12]}"
    return ref["repo"]


def default_title(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    title = f"{parts.hostname}{path}" if path else (parts.hostname or url)
    return title[:200]


class _WebOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme not in ("http", "https"):
            raise PreviewError("Redirected outside the web.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_WebOnly)


class _Head(HTMLParser):
    """Collects <title> and the description / Open Graph <meta> tags of the head."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta: dict[str, str] = {}
        self._in_title = False
        self.done = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            values = {k.lower(): (v or "") for k, v in attrs}
            key = (values.get("property") or values.get("name") or "").lower()
            if key in ("og:title", "og:description", "og:site_name", "description", "twitter:title"):
                self.meta.setdefault(key, values.get("content", ""))
        elif tag == "body":
            self.done = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "head":
            self.done = True

    def handle_data(self, data):
        if self._in_title and len(self.title) < 500:
            self.title += data


def _clean(text: str, limit: int) -> str:
    return " ".join(text.split())[:limit]


def parse_head(html: str) -> dict[str, str]:
    parser = _Head()
    for start in range(0, len(html), 8192):
        parser.feed(html[start : start + 8192])
        if parser.done:
            break
    title = parser.meta.get("og:title") or parser.meta.get("twitter:title") or parser.title
    found = {
        "title": _clean(title, 200),
        "description": _clean(parser.meta.get("og:description") or parser.meta.get("description", ""), 500),
        "site": _clean(parser.meta.get("og:site_name", ""), 100),
    }
    return {key: value for key, value in found.items() if value}


def fetch(url: str) -> dict[str, str]:
    """Title, description and site of a web page; raises PreviewError with a readable reason."""
    if urlsplit(url).scheme not in ("http", "https"):
        raise PreviewError("Only web addresses are fetched.")
    request = urllib.request.Request(  # noqa: S310  (scheme checked above and on every redirect)
        url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    )
    try:
        with _opener.open(request, timeout=TIMEOUT) as response:  # nosec B310
            kind = response.headers.get_content_type()
            if kind not in ("text/html", "application/xhtml+xml"):
                return {"content_type": kind}
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(MAX_BYTES)
    except urllib.error.HTTPError as exc:
        raise PreviewError(f"The site answered {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise PreviewError(f"Could not reach the site ({reason}).") from exc
    try:
        html = raw.decode(charset, errors="replace")
    except LookupError:
        html = raw.decode("utf-8", errors="replace")
    return parse_head(html)
