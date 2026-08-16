from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse, urlunparse

from interview_pipeline.http import HttpError, fetch
from interview_pipeline.models import Episode, Show, TranscriptResult

_MIN_TRANSCRIPT_CHARS = 800
_PAYWALL_MARKERS = re.compile(
    r"(subscribe to read|this post is for paying subscribers|already a paid subscriber|"
    r"members only|log in to (continue|read)|sign in to (continue|read)|paywall)",
    re.I,
)
_LOGIN_MARKERS = re.compile(
    r"(create a free account|become a member to read|login required|sign in to view the transcript)",
    re.I,
)


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False
        self._pending_speaker = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = True
        if tag in {"p", "div", "br", "h1", "h2", "h3", "h4", "li", "tr"}:
            self._chunks.append("\n")
        if tag in {"strong", "b", "h3", "h4"}:
            self._pending_speaker = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = False
        if tag in {"p", "div", "h1", "h2", "h3", "h4", "li"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = unescape(data)
        if text.strip():
            self._chunks.append(text)

    def text(self) -> str:
        raw = "".join(self._chunks)
        raw = re.sub(r"[ \t]{2,}", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def html_to_text(html: str) -> str:
    parser = _HTMLText()
    parser.feed(html)
    parser.close()
    return parser.text()


def looks_like_transcript(text: str) -> bool:
    if not text or len(text.strip()) < 400:
        return False
    speaker_turns = len(re.findall(r"(?m)^(?:\[[^\]]+\]\s*)?[A-Z][\w .'-]{1,40}:\s+\S", text))
    timestamp_turns = len(re.findall(r"(?m)^\[\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\]", text))
    bold_speakers = len(re.findall(r"(?m)^[A-Z][A-Za-z .'-]{1,40}\n", text))
    return (speaker_turns + timestamp_turns + bold_speakers) >= 4


def parse_cheeky_transcript(text: str) -> str:
    """Normalize Transistor timestamp transcripts to markdown speaker turns."""
    lines = text.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    speaker = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf, speaker
        body = " ".join(part.strip() for part in buf if part.strip())
        if speaker and body:
            out.append(f"{speaker}: {body}")
        buf = []

    header = re.compile(r"^\[(\d{1,2}:\d{2}:\d{2}(?:\.\d+)?)\]\s*(.+?)\s*$")
    for line in lines:
        match = header.match(line)
        if match:
            flush()
            speaker = match.group(2).strip()
            continue
        if line.strip():
            buf.append(line)
    flush()
    return "\n\n".join(out) if out else text.strip()


def extract_substack_body_transcript(body_html: str) -> str | None:
    if not body_html:
        return None
    match = re.search(r"(?is)<h[1-4][^>]*>\s*(?:<[^>]+>\s*)*transcript(?:\s*</[^>]+>)*\s*</h[1-4]>", body_html)
    if not match:
        return None
    after = body_html[match.end() :]
    after = re.split(r'(?is)<h[1-4][^>]*>\s*(?:<[^>]+>\s*)*(?:comments|discussion|subscribe)', after)[0]
    text = html_to_text(after)
    text = _normalize_speaker_blocks(text)
    return text if looks_like_transcript(text) else None


def _normalize_speaker_blocks(text: str) -> str:
    """Turn 'Name\\nparagraph' blocks into 'Name: paragraph'."""
    lines = [line.strip() for line in text.splitlines()]
    out: list[str] = []
    i = 0
    name_re = re.compile(r"^[A-Z][\w .'-]{1,50}$")
    while i < len(lines):
        line = lines[i]
        if name_re.match(line) and i + 1 < len(lines) and lines[i + 1] and not name_re.match(lines[i + 1]):
            speaker = line
            i += 1
            chunks: list[str] = []
            while i < len(lines) and lines[i] and not name_re.match(lines[i]):
                if re.match(r"^\d{1,2}:\d{2}:\d{2}", lines[i]):
                    break
                chunks.append(lines[i])
                i += 1
            if chunks:
                out.append(f"{speaker}: {' '.join(chunks)}")
            continue
        if line:
            out.append(line)
        i += 1
    return "\n\n".join(out)


def substack_segments_to_text(segments: list[dict]) -> str:
    turns: list[tuple[str, str]] = []
    current_speaker = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf, current_speaker
        body = " ".join(buf).strip()
        if current_speaker and body:
            turns.append((current_speaker, body))
        buf = []

    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        speaker = None
        words = seg.get("words") or []
        if words:
            speaker = words[0].get("speaker")
        speaker = speaker or seg.get("speaker") or "Speaker"
        if speaker != current_speaker:
            flush()
            current_speaker = speaker
        buf.append(text)
    flush()
    return "\n\n".join(f"{speaker}: {body}" for speaker, body in turns)


def _substack_api_url(episode_url: str) -> str | None:
    parsed = urlparse(episode_url)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[-2] == "p":
        slug = parts[-1]
        api = urlunparse((parsed.scheme, parsed.netloc, f"/api/v1/posts/{slug}", "", "", ""))
        return api
    return None


def _substack_audience_gated(post: dict) -> bool:
    audience = (post.get("audience") or "").lower()
    if audience in {"only_paid", "only-paid", "paid"}:
        return True
    if post.get("free_unlock_required"):
        return True
    return False


def fetch_substack_transcript(episode: Episode) -> TranscriptResult:
    if not episode.url:
        return TranscriptResult("missing", detail="No episode URL for Substack post")
    api = _substack_api_url(episode.url)
    if not api:
        return TranscriptResult("missing", detail="Could not derive Substack API URL")
    try:
        post = fetch(api, accept="application/json").json()
    except HttpError as exc:
        if exc.status in {401, 403}:
            return TranscriptResult("paywalled", source_url=api, source_kind="substack", detail=str(exc))
        return TranscriptResult("error", source_url=api, source_kind="substack", detail=str(exc))

    if _substack_audience_gated(post):
        return TranscriptResult(
            "paywalled",
            source_url=episode.url,
            source_kind="substack",
            detail=f"Substack audience={post.get('audience')}; not fetching around the paywall",
        )

    body_html = post.get("body_html") or ""
    from_body = extract_substack_body_transcript(body_html)
    if from_body:
        return TranscriptResult(
            "found",
            text=from_body,
            source_url=episode.url,
            source_kind="substack_body",
            detail="Official transcript section on the public Substack post",
        )

    upload = post.get("podcastUpload") or {}
    transcription = upload.get("transcription") or {}
    if (transcription.get("status") or "").lower() != "transcribed":
        video = post.get("videoUpload") or {}
        extracted = (video.get("extractedAudio") or {}).get("transcription") or {}
        if (extracted.get("status") or "").lower() == "transcribed":
            transcription = extracted

    cdn = transcription.get("cdn_url")
    if cdn and (transcription.get("status") or "").lower() == "transcribed":
        try:
            payload = fetch(cdn, accept="application/json").json()
        except HttpError as exc:
            return TranscriptResult("error", source_url=episode.url, source_kind="substack", detail=str(exc))
        if isinstance(payload, list) and payload:
            text = substack_segments_to_text(payload)
            if looks_like_transcript(text):
                return TranscriptResult(
                    "found",
                    text=text,
                    source_url=episode.url,
                    source_kind="substack_player",
                    detail="Official Substack player transcription on a public post",
                )

    if _PAYWALL_MARKERS.search(body_html):
        return TranscriptResult(
            "paywalled",
            source_url=episode.url,
            source_kind="substack",
            detail="Paywall markers on post and no public transcript section",
        )
    return TranscriptResult(
        "missing",
        source_url=episode.url,
        source_kind="substack",
        detail="Public post has no official transcript section",
    )


def fetch_rss_transcript(episode: Episode) -> TranscriptResult:
    if not episode.rss_transcript_url:
        return TranscriptResult("missing", detail="No podcast:transcript URL in the RSS item")
    try:
        response = fetch(episode.rss_transcript_url, accept="text/plain, text/vtt, application/json, */*")
    except HttpError as exc:
        if exc.status in {401, 403}:
            return TranscriptResult(
                "paywalled",
                source_url=episode.rss_transcript_url,
                source_kind="rss_transcript",
                detail=str(exc),
            )
        return TranscriptResult("error", source_url=episode.rss_transcript_url, source_kind="rss_transcript", detail=str(exc))

    text = response.text()
    ctype = response.content_type.lower()
    if "json" in ctype:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, list):
            text = substack_segments_to_text(payload)
    else:
        text = parse_cheeky_transcript(text)
    if looks_like_transcript(text):
        return TranscriptResult(
            "found",
            text=text,
            source_url=episode.rss_transcript_url,
            source_kind="rss_transcript",
            detail="Official podcast:transcript from the show RSS feed",
        )
    return TranscriptResult(
        "missing",
        source_url=episode.rss_transcript_url,
        source_kind="rss_transcript",
        detail="RSS transcript URL did not contain a usable official transcript",
    )


def _lex_transcript_url(episode_url: str) -> str | None:
    parsed = urlparse(episode_url)
    path = parsed.path.rstrip("/")
    if not path:
        return None
    if path.endswith("-transcript"):
        candidate = path
    else:
        candidate = f"{path}-transcript"
    return urlunparse((parsed.scheme, parsed.netloc, candidate, "", "", ""))


def fetch_lex_transcript(episode: Episode) -> TranscriptResult:
    url = _lex_transcript_url(episode.url)
    if not url:
        return TranscriptResult("missing", detail="No Lex episode URL")
    try:
        html = fetch(url, accept="text/html").text()
    except HttpError as exc:
        if exc.status == 404:
            return TranscriptResult("missing", source_url=url, source_kind="lex", detail="No official -transcript page")
        return TranscriptResult("error", source_url=url, source_kind="lex", detail=str(exc))
    if _PAYWALL_MARKERS.search(html) or _LOGIN_MARKERS.search(html):
        return TranscriptResult("paywalled", source_url=url, source_kind="lex", detail="Login/paywall markers on transcript page")
    text = html_to_text(html)
    # Keep from the first timestamp or speaker heading onward when possible.
    cut = re.search(r"(?m)^(?:Transcript|\d{1,2}:\d{2}|\[\d{1,2}:\d{2})", text)
    if cut:
        text = text[cut.start() :]
    text = _normalize_speaker_blocks(text)
    if looks_like_transcript(text):
        return TranscriptResult(
            "found",
            text=text,
            source_url=url,
            source_kind="lex",
            detail="Official Lex Fridman transcript page",
        )
    return TranscriptResult("missing", source_url=url, source_kind="lex", detail="Transcript page lacked speaker turns")


def fetch_colossus_transcript(episode: Episode) -> TranscriptResult:
    if not episode.url:
        return TranscriptResult("missing", detail="No Colossus episode URL")
    try:
        html = fetch(episode.url, accept="text/html").text()
    except HttpError as exc:
        if exc.status in {401, 403}:
            return TranscriptResult("paywalled", source_url=episode.url, source_kind="colossus", detail=str(exc))
        return TranscriptResult("error", source_url=episode.url, source_kind="colossus", detail=str(exc))

    text = html_to_text(html)
    if looks_like_transcript(text):
        return TranscriptResult(
            "found",
            text=_normalize_speaker_blocks(text),
            source_url=episode.url,
            source_kind="colossus",
            detail="Official transcript text present on the public Colossus page",
        )
    return TranscriptResult(
        "paywalled",
        source_url=episode.url,
        source_kind="colossus",
        detail="Colossus/ILTB transcript is not on the public page; treating as login-gated",
    )


def fetch_official_transcript(episode: Episode, show: Show) -> TranscriptResult:
    """Fetch an official transcript only. Never invent one. Never bypass login/paywall."""
    if episode.rss_transcript_url:
        result = fetch_rss_transcript(episode)
        if result.status in {"found", "paywalled"}:
            return result

    kind = show.transcript
    if kind == "substack":
        return fetch_substack_transcript(episode)
    if kind == "lex":
        return fetch_lex_transcript(episode)
    if kind == "colossus":
        return fetch_colossus_transcript(episode)
    if kind == "rss_podcast_transcript":
        return fetch_rss_transcript(episode)
    return TranscriptResult(
        "missing",
        source_url=episode.url or None,
        source_kind=kind,
        detail="No official public transcript source configured for this show",
    )
