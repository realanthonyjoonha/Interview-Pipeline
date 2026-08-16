from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Show:
    id: str
    name: str
    tier: str
    enabled: bool
    feed_url: str
    site: str
    transcript: str
    filter: str
    notes: str = ""
    hosts: tuple[str, ...] = ()


@dataclass
class Episode:
    show_id: str
    show_name: str
    title: str
    published: str
    url: str
    guid: str
    duration_seconds: int | None
    description: str = ""
    rss_transcript_url: str | None = None
    audio_url: str | None = None
    watched_people: list[str] = field(default_factory=list)

    @property
    def duration_minutes(self) -> float | None:
        if self.duration_seconds is None:
            return None
        return self.duration_seconds / 60.0

    @property
    def slug(self) -> str:
        date = (self.published or "undated")[:10]
        return f"{date}-{_slugify(self.title)}"


@dataclass(frozen=True)
class FilterDecision:
    matched: bool
    reasons: tuple[str, ...]
    guest_hint: str | None = None


@dataclass
class TranscriptResult:
    status: str
    text: str | None = None
    source_url: str | None = None
    source_kind: str | None = None
    detail: str | None = None
    derived_from_audio: bool = False

    @property
    def found(self) -> bool:
        return self.status == "found" and bool(self.text and self.text.strip())


@dataclass
class ReportResult:
    written: bool
    path: str | None = None
    reason: str | None = None


def episode_record(
    episode: Episode,
    decision: FilterDecision,
    transcript: TranscriptResult | None = None,
    report: ReportResult | None = None,
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "id": f"{episode.show_id}/{episode.slug}",
        "show_id": episode.show_id,
        "show_name": episode.show_name,
        "title": episode.title,
        "published": episode.published,
        "url": episode.url,
        "guid": episode.guid,
        "duration_seconds": episode.duration_seconds,
        "duration_minutes": round(episode.duration_minutes, 1)
        if episode.duration_minutes is not None
        else None,
        "watched_people": episode.watched_people,
        "filter": {
            "matched": decision.matched,
            "reasons": list(decision.reasons),
            "guest_hint": decision.guest_hint,
        },
    }
    if transcript is not None:
        rec["transcript"] = {
            "status": transcript.status,
            "source_url": transcript.source_url,
            "source_kind": transcript.source_kind,
            "detail": transcript.detail,
            "character_count": len(transcript.text) if transcript.text else 0,
            "derived_from_audio": transcript.derived_from_audio,
        }
    if report is not None:
        rec["report"] = asdict(report)
    return rec


def _slugify(value: str, max_len: int = 80) -> str:
    out = []
    prev_dash = False
    for ch in value.lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    slug = "".join(out).strip("-")
    return slug[:max_len].strip("-") or "episode"
