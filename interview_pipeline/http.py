from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from interview_pipeline.catalog import user_agent

_LAST_FETCH_AT = 0.0


@dataclass
class HttpResponse:
    url: str
    status: int
    content_type: str
    body: bytes
    final_url: str

    def text(self, encoding: str = "utf-8") -> str:
        return self.body.decode(encoding, errors="replace")

    def json(self):
        return json.loads(self.text())


class HttpError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, url: str | None = None):
        super().__init__(message)
        self.status = status
        self.url = url


def fetch(
    url: str,
    *,
    timeout: int = 30,
    pause_s: float = 0.4,
    accept: str | None = None,
) -> HttpResponse:
    """Fetch a public URL. No cookies, no login, no paywall bypass."""
    global _LAST_FETCH_AT
    wait = pause_s - (time.monotonic() - _LAST_FETCH_AT)
    if wait > 0:
        time.sleep(wait)

    headers = {
        "User-Agent": user_agent(),
        "Accept": accept or "application/rss+xml, application/json, text/html, text/plain, */*",
    }
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            result = HttpResponse(
                url=url,
                status=getattr(response, "status", 200) or 200,
                content_type=response.headers.get("content-type") or "",
                body=body,
                final_url=response.geturl(),
            )
    except urllib.error.HTTPError as exc:
        _LAST_FETCH_AT = time.monotonic()
        snippet = ""
        try:
            snippet = exc.read()[:200].decode("utf-8", "replace")
        except Exception:
            snippet = ""
        raise HttpError(
            f"HTTP {exc.code} for {url}: {snippet}",
            status=exc.code,
            url=url,
        ) from exc
    except urllib.error.URLError as exc:
        _LAST_FETCH_AT = time.monotonic()
        raise HttpError(f"Failed to fetch {url}: {exc}", url=url) from exc

    _LAST_FETCH_AT = time.monotonic()
    return result
