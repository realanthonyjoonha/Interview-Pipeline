from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from interview_pipeline.models import Episode, ReportResult, TranscriptResult
from interview_pipeline.transcripts import (
    _normalize_speaker_blocks,
    is_speaker_name,
    parse_cheeky_transcript,
)

_MIN_TURNS = 4
_MIN_CHARS = 800
_MAX_REPORT_CHARS = 40_000
_SPONSOR = re.compile(
    r"(sponsor|sponsored by|discount code|use code|subscribe at|patreon|"
    r"this episode is brought to you)",
    re.I,
)
_BACKCHANNEL = re.compile(
    r"^(yeah|yes|yep|right|ok|okay|mm-?hmm|mhm|thanks|thank you|got it|sure|exactly|wow)\.?$",
    re.I,
)
_QUANTITY = re.compile(
    r"(\$\s?\d|"
    r"\b\d[\d,]*(?:\.\d+)?\s*(%|percent|x\b|million|billion|trillion|gpuc?s?|mw|gw|dollars?)|"
    r"\b\d{1,3}(?:,\d{3})+\b|"
    r"\b\d+\s*(users|people|members|employees))",
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
    r"I push back|contrary to|vs\.|versus|I'm skeptical|"
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


@dataclass
class Cluster:
    speaker: str
    texts: list[str]

    @property
    def text(self) -> str:
        return " ".join(self.texts)


def parse_turns(transcript: str) -> list[Turn]:
    normalized = _normalize_speaker_blocks(parse_cheeky_transcript(transcript))
    turns: list[Turn] = []
    for match in _TURN.finditer(normalized):
        text = re.sub(r"\s+", " ", match.group("text")).strip()
        if not text:
            continue
        speaker = match.group("speaker").strip()
        if not is_speaker_name(speaker):
            continue
        turns.append(
            Turn(
                speaker=speaker,
                text=text,
                timestamp=match.group("ts"),
            )
        )
    return turns


def is_usable_transcript(text: str | None, *, audio_derived: bool = False) -> bool:
    if not text or len(text.strip()) < _MIN_CHARS:
        return False
    turns = parse_turns(text)
    if len(turns) >= _MIN_TURNS:
        return True
    if audio_derived:
        sentences = [s for s in re.split(r"[.!?]+", text) if len(s.split()) >= 5]
        return len(sentences) >= 8
    return False


def _sentences(text: str) -> list[str]:
    raw = re.sub(r"\s+", " ", text).strip()
    if not raw:
        return []
    parts = re.split(r"(?<=[.!?])\s+", raw)
    out: list[str] = []
    for part in parts:
        sentence = part.strip()
        if not sentence:
            continue
        if sentence[-1] not in ".!?":
            sentence = sentence.rstrip(" ,;:") + "."
        out.append(sentence)
    return out


def _complete_brief(text: str, *, max_sentences: int = 4) -> str:
    sentences = _sentences(text)
    if not sentences:
        return ""
    kept: list[str] = []
    words = 0
    for sentence in sentences:
        extra = len(sentence.split())
        if kept and words + extra > 120:
            break
        kept.append(sentence)
        words += extra
        if len(kept) >= max_sentences:
            break
    return " ".join(kept)


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
    return len(words) >= 22


_QUESTION_START = re.compile(
    r"^(do|does|did|what|why|how|can|could|would|is|are|who|where|when|which|any other)\b",
    re.I,
)
_INTRO = re.compile(
    r"^(welcome|today I('m| am) (chatting|talking)|thanks\.|that is the end|give me the)\b",
    re.I,
)


def _is_prompt(text: str) -> bool:
    stripped = text.strip()
    if _INTRO.search(stripped):
        return True
    if stripped.endswith("?") and not _NUMBER.search(stripped) and not _DISAGREE.search(stripped):
        return True
    if _QUESTION_START.search(stripped) and not _NUMBER.search(stripped):
        return True
    return False


def _cluster_score(cluster: Cluster) -> tuple[int, int]:
    text = cluster.text
    score = 0
    if _NUMBER.search(text):
        score += 3
    if _CAVEAT.search(text):
        score += 2
    if _DISAGREE.search(text):
        score += 2
    score += min(len(text.split()) // 20, 3)
    return (score, len(text.split()))


_GENERIC_SPEAKERS = {"Speaker", "SPEAKER", "SPEAKER_00", "SPEAKER_01", "SPEAKER_02"}


def _clusters(turns: list[Turn]) -> list[Cluster]:
    speakers = {turn.speaker for turn in turns}
    merge_same = not (len(speakers) == 1 and next(iter(speakers)) in _GENERIC_SPEAKERS)
    clusters: list[Cluster] = []
    for turn in turns:
        if not _noteworthy(turn):
            continue
        if _is_prompt(turn.text):
            continue
        if merge_same and clusters and clusters[-1].speaker == turn.speaker:
            clusters[-1].texts.append(turn.text)
        else:
            clusters.append(Cluster(speaker=turn.speaker, texts=[turn.text]))
    ranked = sorted(clusters, key=_cluster_score, reverse=True)
    # Keep the strongest arguments, then restore transcript order.
    keep = {id(cluster) for cluster in ranked[:18]}
    return [cluster for cluster in clusters if id(cluster) in keep]


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
    derived_from_audio: bool = False,
) -> str:
    turns = parse_turns(transcript_text)
    if not turns and derived_from_audio:
        turns = [
            Turn(speaker="Speaker", text=para.strip())
            for para in re.split(r"\n\s*\n", transcript_text)
            if para.strip()
        ]
    clusters = _clusters(turns)
    speakers = []
    for turn in turns:
        if turn.speaker not in speakers:
            speakers.append(turn.speaker)

    if derived_from_audio:
        kind = "decision-support / time-saving notes from an audio-derived transcript"
        source_note = (
            "Audio-derived (local whisper.cpp). These are not official-page quotes. "
            "Speaker labels may be unlabeled or generic."
        )
        attribution = (
            "Attributed from the audio transcript. Wording is condensed from complete "
            "speaker sentences, not invented, and not taken from recaps."
        )
    else:
        kind = "decision-support / time-saving notes from an official transcript"
        source_note = transcript_source or "official transcript"
        attribution = (
            "Attributed to the speaker. Wording is condensed from complete transcript "
            "sentences, not invented."
        )

    lines: list[str] = [
        f"# {title}",
        "",
        f"- Kind: {kind}",
        "- Not a house view. No buy/sell. No investment-desk framing.",
        f"- Show: {show_name or 'unknown'}",
        f"- Published: {published or 'unknown'}",
        f"- Episode URL: {url or 'unknown'}",
        f"- Duration: {duration_minutes:.0f} min" if duration_minutes is not None else "- Duration: unknown",
        f"- Guest hint from title: {guest_hint}" if guest_hint else "- Guest hint from title: none",
        f"- Speakers in transcript: {', '.join(speakers) if speakers else 'unlabeled'}",
        f"- Transcript source: {source_note}",
        f"- Watched people named in title/description: {', '.join(watched_people)}"
        if watched_people
        else "- Watched people named in title/description: none",
        "",
        "## Main points",
        "",
        attribution,
        "",
    ]

    if not clusters:
        lines.append("No noteworthy speaker turns passed the extractive bar.")
        lines.append("")
    else:
        for cluster in clusters:
            brief = _complete_brief(cluster.text)
            if not brief:
                continue
            who = cluster.speaker
            if derived_from_audio and who in {"Speaker", "SPEAKER", "SPEAKER_00"} and guest_hint:
                who = f"{who} (guest hint: {guest_hint})"
            lines.append(f"- **{who}:** {brief}")
        lines.append("")

    number_lines: list[str] = []
    caveat_lines: list[str] = []
    disagree_lines: list[str] = []
    for cluster in clusters:
        for sentence in _sentences(cluster.text):
            if _QUANTITY.search(sentence):
                number_lines.append(f"- {cluster.speaker}: {sentence}")
            if _CAVEAT.search(sentence):
                caveat_lines.append(f"- {cluster.speaker}: {sentence}")
            if _DISAGREE.search(sentence):
                disagree_lines.append(f"- {cluster.speaker}: {sentence}")

    lines.extend(["## Numbers they stated", ""])
    if number_lines:
        # Deduplicate while keeping order
        seen: set[str] = set()
        for item in number_lines:
            if item in seen:
                continue
            seen.add(item)
            lines.append(item)
    else:
        lines.append("- No explicit numbers were extracted from speaker turns.")
    lines.append("")

    lines.extend(["## Caveats and disagreements", ""])
    if caveat_lines or disagree_lines:
        seen = set()
        for item in caveat_lines + disagree_lines:
            if item in seen:
                continue
            seen.add(item)
            lines.append(item)
    else:
        lines.append("- No explicit caveats or disagreements were extracted.")
    lines.append("")

    if transcript_status_note:
        lines.extend(["## Notes", "", transcript_status_note, ""])
    else:
        notes = [
            "This file is an extractive main-points brief for later editing.",
            "If a claim is not in the transcript, it is not here.",
        ]
        if derived_from_audio:
            notes.append("Do not treat audio-derived lines as official-page quotations.")
        lines.extend(["## Notes", "", " ".join(notes), ""])

    report = "\n".join(lines).strip() + "\n"
    if len(report) > _MAX_REPORT_CHARS:
        report = (
            report[:_MAX_REPORT_CHARS].rsplit("\n", 1)[0]
            + "\n\n<!-- truncated to keep the note readable -->\n"
        )
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
            reason=f"no usable transcript ({status}): {detail}. Refusing to write a report.",
        )
    if not is_usable_transcript(transcript.text, audio_derived=transcript.derived_from_audio):
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
        derived_from_audio=transcript.derived_from_audio,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(markdown, encoding="utf-8")
    return ReportResult(written=True, path=str(destination), reason=None)
