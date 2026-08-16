from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from interview_pipeline.models import Episode, ReportResult, TranscriptResult

_MIN_TURNS = 4
_MIN_CHARS = 800
_MAX_REPORT_CHARS = 55_000  # roughly the high end of a 5–20 page note
_SPONSOR = re.compile(
    r"(sponsor|sponsored by|discount code|use code|subscribe at|patreon|shopify|"
    r"this episode is brought to you)",
    re.I,
)
_BACKCHANNEL = re.compile(
    r"^(yeah|yes|yep|right|ok|okay|mm-?hmm|mhm|thanks|thank you|got it|sure|exactly|wow)\.?$",
    re.I,
)
_NUMBER = re.compile(
    r"(\b\d[\d,]*(?:\.\d+)?\s*(%|percent|x|k|m|b|million|billion|trillion|gpuc?s?|"
    r"mw|gw|tb|gb|ms|hours?|minutes?|years?|months?|weeks?|dollars?|usd)?\b|\$\s?\d)",
    re.I,
)
_CAVEAT = re.compile(
    r"\b(caveat|however|but I|I don't know|I do not know|uncertain|not sure|"
    r"I might be wrong|we haven't|we have not|the risk|I could be off|"
    r"don't quote me|roughly|approximately|maybe|probably not)\b",
    re.I,
)
_DISAGREE = re.compile(
    r"\b(I disagree|I don't think|I do not think|that's wrong|that is wrong|"
    r"I push back|contrary to|vs\.|versus|I push back|I'm skeptical|"
    r"I am skeptical|I don't buy|I do not buy)\b",
    re.I,
)
_TURN = re.compile(
    r"(?m)^(?:\[(?P<ts>[^\]]+)\]\s*)?(?P<speaker>[A-Z][A-Za-z0-9_ .'-]{0,50}):\s+(?P<text>.+)$"
)


@dataclass(frozen=True)
class Turn:
    speaker: str
    text: str
    timestamp: str | None = None


def parse_turns(transcript: str) -> list[Turn]:
    turns: list[Turn] = []
    for match in _TURN.finditer(transcript):
        text = re.sub(r"\s+", " ", match.group("text")).strip()
        if not text:
            continue
        turns.append(
            Turn(
                speaker=match.group("speaker").strip(),
                text=text,
                timestamp=match.group("ts"),
            )
        )
    return turns


def is_usable_transcript(text: str | None) -> bool:
    if not text or len(text.strip()) < _MIN_CHARS:
        return False
    return len(parse_turns(text)) >= _MIN_TURNS


def _noteworthy(turn: Turn) -> bool:
    if _BACKCHANNEL.match(turn.text.strip()):
        return False
    if _SPONSOR.search(turn.text) and len(turn.text.split()) < 40:
        return False
    words = turn.text.split()
    if len(words) < 12 and not _NUMBER.search(turn.text) and not _DISAGREE.search(turn.text):
        return False
    if _NUMBER.search(turn.text) or _CAVEAT.search(turn.text) or _DISAGREE.search(turn.text):
        return True
    return len(words) >= 28


def _excerpt(text: str, limit: int = 420) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + "…"


def build_report_markdown(
    *,
    transcript_text: str,
    title: str,
    show_name: str = "",
    published: str = "",
    url: str = "",
    duration_minutes: float | None = None,
    guest_hint: str | None = None,
    watched_people: list[str] | None = None,
    transcript_source: str | None = None,
    transcript_status_note: str | None = None,
) -> str:
    turns = parse_turns(transcript_text)
    noteworthy = [turn for turn in turns if _noteworthy(turn)]
    numbers = [turn for turn in noteworthy if _NUMBER.search(turn.text)]
    caveats = [turn for turn in noteworthy if _CAVEAT.search(turn.text)]
    disagreements = [turn for turn in noteworthy if _DISAGREE.search(turn.text)]

    speakers = []
    for turn in turns:
        if turn.speaker not in speakers:
            speakers.append(turn.speaker)

    lines: list[str] = [
        f"# {title}",
        "",
        "- Kind: decision-support / time-saving notes from an official transcript",
        "- Not a house view. No buy/sell. No investment-desk framing.",
        f"- Show: {show_name or 'unknown'}",
        f"- Published: {published or 'unknown'}",
        f"- Episode URL: {url or 'unknown'}",
        f"- Duration: {duration_minutes:.0f} min" if duration_minutes is not None else "- Duration: unknown",
        f"- Guest hint from title: {guest_hint}" if guest_hint else "- Guest hint from title: none",
        f"- Speakers in transcript: {', '.join(speakers) if speakers else 'unlabeled'}",
        f"- Transcript source: {transcript_source or 'official transcript'}",
        f"- Watched people named in title/description: {', '.join(watched_people)}"
        if watched_people
        else "- Watched people named in title/description: none",
        "",
        "## Main points",
        "",
        "Attributed to the speaker. Wording is excerpted from the official transcript, not invented.",
        "",
    ]

    if not noteworthy:
        lines.append("No noteworthy speaker turns passed the extractive bar. See caveats.")
        lines.append("")
    else:
        by_speaker: dict[str, list[Turn]] = {}
        for turn in noteworthy:
            by_speaker.setdefault(turn.speaker, []).append(turn)
        for speaker, speaker_turns in by_speaker.items():
            lines.append(f"### {speaker}")
            lines.append("")
            for turn in speaker_turns:
                stamp = f" ({turn.timestamp})" if turn.timestamp else ""
                lines.append(f"-{stamp} {speaker} said: “{_excerpt(turn.text)}”")
            lines.append("")

    lines.extend(["## Numbers and specifics", ""])
    if numbers:
        for turn in numbers:
            lines.append(f"- {turn.speaker}: “{_excerpt(turn.text, 360)}”")
    else:
        lines.append("- No explicit numbers were extracted from speaker turns.")
    lines.append("")

    lines.extend(["## Caveats and disagreements", ""])
    if caveats or disagreements:
        for turn in caveats:
            lines.append(f"- Caveat — {turn.speaker}: “{_excerpt(turn.text, 360)}”")
        for turn in disagreements:
            lines.append(f"- Disagreement — {turn.speaker}: “{_excerpt(turn.text, 360)}”")
    else:
        lines.append("- No explicit caveats or disagreements were extracted.")
    lines.append("")

    if transcript_status_note:
        lines.extend(["## Notes", "", transcript_status_note, ""])
    else:
        lines.extend(
            [
                "## Notes",
                "",
                "This file is extractive notes for later editing. If a claim is not in the transcript, it is not here.",
                "",
            ]
        )

    report = "\n".join(lines).strip() + "\n"
    if len(report) > _MAX_REPORT_CHARS:
        report = report[:_MAX_REPORT_CHARS].rsplit("\n", 1)[0] + "\n\n<!-- truncated to keep the note in the 5–20 page band -->\n"
    return report


def write_report(
    *,
    transcript: TranscriptResult | None,
    destination: Path,
    episode: Episode | None = None,
    title: str | None = None,
    show_name: str | None = None,
    guest_hint: str | None = None,
) -> ReportResult:
    if transcript is None or not transcript.found:
        status = transcript.status if transcript else "missing"
        detail = transcript.detail if transcript else "No transcript provided"
        return ReportResult(
            written=False,
            path=None,
            reason=f"no official transcript ({status}): {detail}. Refusing to write a report.",
        )
    if not is_usable_transcript(transcript.text):
        return ReportResult(
            written=False,
            path=None,
            reason="transcript is missing speaker turns or is too short to be a real interview transcript. Refusing to write a report from recaps.",
        )

    markdown = build_report_markdown(
        transcript_text=transcript.text or "",
        title=title or (episode.title if episode else "Untitled episode"),
        show_name=show_name or (episode.show_name if episode else ""),
        published=episode.published if episode else "",
        url=episode.url if episode else "",
        duration_minutes=episode.duration_minutes if episode else None,
        guest_hint=guest_hint,
        watched_people=list(episode.watched_people) if episode else None,
        transcript_source=transcript.source_url or transcript.source_kind,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(markdown, encoding="utf-8")
    return ReportResult(written=True, path=str(destination), reason=None)
