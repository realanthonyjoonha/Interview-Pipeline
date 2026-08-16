from __future__ import annotations

from pathlib import Path

from interview_pipeline.audio import transcribe_episode_audio
from interview_pipeline.models import Episode, Show, TranscriptResult
from interview_pipeline.transcripts import fetch_official_transcript


def resolve_transcript(
    episode: Episode,
    show: Show,
    *,
    work_dir: Path,
    skip_audio: bool = False,
    official_fn=None,
    download_fn=None,
    transcribe_fn=None,
    whisper_bin: str | None = None,
    whisper_model: str | None = None,
) -> TranscriptResult:
    """Prefer an official public transcript. If none, transcribe the RSS audio."""
    fetcher = official_fn or fetch_official_transcript
    official = fetcher(episode, show)
    if official.found:
        official.derived_from_audio = False
        return official
    if skip_audio:
        return official
    audio = transcribe_episode_audio(
        episode,
        work_dir=work_dir,
        download_fn=download_fn,
        transcribe_fn=transcribe_fn,
        whisper_bin=whisper_bin,
        whisper_model=whisper_model,
    )
    if audio.found:
        return audio
    # Keep the official miss, but attach the audio attempt.
    if audio.status == "error" or audio.detail:
        official.detail = (
            f"{official.detail or official.status}; audio fallback: {audio.detail or audio.status}"
        )
        if not official.source_kind:
            official.source_kind = audio.source_kind
    return official if official.status != "found" else audio
