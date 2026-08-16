from pathlib import Path

from interview_pipeline.audio import TranscriptionError, _parse_whisper_srt, transcribe_episode_audio
from interview_pipeline.models import Episode, Show, TranscriptResult
from interview_pipeline.reports import write_report
from interview_pipeline.resolve import resolve_transcript
from interview_pipeline.transcripts import fetch_colossus_transcript

FIXTURE = Path(__file__).parent / "fixtures" / "sample_transcript.md"


def _show() -> Show:
    return Show(
        id="no_priors",
        name="No Priors",
        tier="core",
        enabled=True,
        feed_url="https://example.test/feed",
        site="",
        transcript="none_known",
        filter="no_priors",
        hosts=("Sarah", "Elad"),
    )


def _episode(*, audio_url: str | None = "https://example.test/ep.mp3") -> Episode:
    return Episode(
        show_id="no_priors",
        show_name="No Priors",
        title="Fixture guest sit with Casey Guest",
        published="2026-08-01",
        url="https://example.test/ep",
        guid="fixture-audio",
        duration_seconds=3600,
        audio_url=audio_url,
    )


def test_missing_official_plus_fixture_audio_writes_audio_derived_report(tmp_path: Path):
    destination = tmp_path / "report.md"
    audio_dir = tmp_path / "audio"

    def official_fn(episode, show):
        return TranscriptResult("missing", detail="No official public transcript")

    def download_fn(url, dest: Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"ID3" + b"\x00" * 200)
        return dest

    def transcribe_fn(path: Path):
        assert path.exists() and path.stat().st_size > 100
        return FIXTURE.read_text(encoding="utf-8")

    transcript = resolve_transcript(
        _episode(),
        _show(),
        work_dir=audio_dir,
        official_fn=official_fn,
        download_fn=download_fn,
        transcribe_fn=transcribe_fn,
    )
    assert transcript.found
    assert transcript.derived_from_audio is True
    assert transcript.source_kind == "audio_whisper"

    result = write_report(
        transcript=transcript,
        destination=destination,
        episode=_episode(),
        guest_hint="Casey Guest",
    )
    assert result.written is True
    text = destination.read_text(encoding="utf-8")
    assert "audio-derived" in text.lower()
    assert "not official-page quotes" in text.lower()
    assert "## Main points" in text
    assert "2 million examples" in text
    assert "said:" not in text


def test_empty_audio_refuses_to_write_report(tmp_path: Path):
    destination = tmp_path / "should-not-exist.md"

    def official_fn(episode, show):
        return TranscriptResult("missing", detail="No official public transcript")

    def download_fn(url, dest: Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"")
        return dest

    transcript = resolve_transcript(
        _episode(),
        _show(),
        work_dir=tmp_path / "audio",
        official_fn=official_fn,
        download_fn=download_fn,
        transcribe_fn=lambda path: "should not be called",
    )
    assert transcript.found is False
    result = write_report(transcript=transcript, destination=destination, title="No")
    assert result.written is False
    assert destination.exists() is False
    assert "Refusing" in (result.reason or "")


def test_failed_transcription_refuses_to_write_report(tmp_path: Path):
    destination = tmp_path / "should-not-exist.md"

    def official_fn(episode, show):
        return TranscriptResult("paywalled", detail="Lenny paid post")

    def download_fn(url, dest: Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"ID3" + b"\x00" * 200)
        return dest

    def transcribe_fn(path: Path):
        raise TranscriptionError("whisper.cpp failed")

    transcript = resolve_transcript(
        _episode(),
        _show(),
        work_dir=tmp_path / "audio",
        official_fn=official_fn,
        download_fn=download_fn,
        transcribe_fn=transcribe_fn,
    )
    assert transcript.found is False
    result = write_report(transcript=transcript, destination=destination, title="No")
    assert result.written is False
    assert destination.exists() is False


def test_no_audio_and_no_official_refuses(tmp_path: Path):
    destination = tmp_path / "should-not-exist.md"

    def official_fn(episode, show):
        return TranscriptResult("missing", detail="No official public transcript")

    transcript = resolve_transcript(
        _episode(audio_url=None),
        _show(),
        work_dir=tmp_path / "audio",
        official_fn=official_fn,
    )
    assert transcript.found is False
    result = write_report(transcript=transcript, destination=destination, title="No")
    assert result.written is False
    assert destination.exists() is False


def test_official_transcript_is_preferred_over_audio(tmp_path: Path):
    called = {"audio": False}

    def official_fn(episode, show):
        return TranscriptResult(
            "found",
            text=FIXTURE.read_text(encoding="utf-8"),
            source_kind="substack_body",
            source_url="https://example.test/official",
        )

    def download_fn(url, dest):
        called["audio"] = True
        raise AssertionError("audio should not be downloaded when official text exists")

    transcript = resolve_transcript(
        _episode(),
        _show(),
        work_dir=tmp_path / "audio",
        official_fn=official_fn,
        download_fn=download_fn,
    )
    assert transcript.found
    assert transcript.derived_from_audio is False
    assert called["audio"] is False


def test_colossus_is_not_scraped():
    episode = _episode(audio_url="https://example.test/iltb.mp3")
    episode.url = "https://colossus.com/episode/sandcastles-and-silicon/"
    result = fetch_colossus_transcript(episode)
    assert result.found is False
    assert "not scraping" in (result.detail or "").lower()


def test_parse_whisper_srt_to_speaker_turns():
    srt = """1
00:00:01,000 --> 00:00:04,000
We trained the last run on 2 million examples.

2
00:00:05,000 --> 00:00:08,000
I disagree that scale alone gets you there.
"""
    text = _parse_whisper_srt(srt)
    assert "[00:00:01] Speaker: We trained the last run on 2 million examples." in text
    assert "I disagree that scale alone" in text


def test_transcribe_episode_audio_empty_download(tmp_path: Path):
    def download_fn(url, dest: Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"xx")
        return dest

    result = transcribe_episode_audio(
        _episode(),
        work_dir=tmp_path,
        download_fn=download_fn,
        transcribe_fn=lambda path: "",
    )
    assert result.found is False
    assert result.derived_from_audio is True
