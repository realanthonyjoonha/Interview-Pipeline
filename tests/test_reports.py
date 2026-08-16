from pathlib import Path

from interview_pipeline.models import Episode, TranscriptResult
from interview_pipeline.reports import build_report_markdown, is_usable_transcript, parse_turns, write_report

FIXTURE = Path(__file__).parent / "fixtures" / "sample_transcript.md"


def test_parse_turns_ignores_colon_sentence_fragments():
    text = (
        "Ryan Greenblatt: Full automation of AI R&D is around 2031.\n\n"
        "Another way to put this is: we do not have the data mix yet.\n\n"
        "Dwarkesh Patel: That number is a median, not a point forecast.\n\n"
        "Host: Thanks for walking through the caveat.\n"
    )
    speakers = {turn.speaker for turn in parse_turns(text)}
    assert speakers == {"Ryan Greenblatt", "Dwarkesh Patel", "Host"}


def test_fixture_transcript_is_usable():
    assert is_usable_transcript(FIXTURE.read_text(encoding="utf-8"))


def test_writes_report_from_fixture_transcript(tmp_path: Path):
    destination = tmp_path / "report.md"
    episode = Episode(
        show_id="fixture",
        show_name="Fixture show",
        title="Fixture interview",
        published="2026-08-01",
        url="https://example.test/fixture",
        guid="fixture",
        duration_seconds=3600,
    )
    result = write_report(
        transcript=TranscriptResult(
            "found",
            text=FIXTURE.read_text(encoding="utf-8"),
            source_url="tests/fixtures/sample_transcript.md",
            source_kind="fixture",
        ),
        destination=destination,
        episode=episode,
        guest_hint="Guest Speaker",
    )
    assert result.written is True
    assert destination.exists()
    text = destination.read_text(encoding="utf-8")
    assert text.startswith("# Fixture interview")
    assert "## Main points" in text
    assert "## Caveats and disagreements" in text
    assert "Guest Speaker said:" in text
    assert "2 million examples" in text
    assert "I disagree that scale alone" in text
    assert "No house view" in text or "Not a house view" in text
    assert "buy/sell" in text


def test_no_transcript_refuses_to_write_report(tmp_path: Path):
    destination = tmp_path / "should-not-exist.md"
    result = write_report(
        transcript=TranscriptResult("missing", detail="No official transcript"),
        destination=destination,
        title="Should not be written",
    )
    assert result.written is False
    assert destination.exists() is False
    assert "Refusing to write a report" in (result.reason or "")


def test_none_transcript_refuses_to_write_report(tmp_path: Path):
    destination = tmp_path / "should-not-exist.md"
    result = write_report(transcript=None, destination=destination)
    assert result.written is False
    assert destination.exists() is False


def test_recap_only_text_is_not_a_transcript(tmp_path: Path):
    recap = (
        "In this episode the host recaps the news. "
        "The guest supposedly said many important things. "
        "This is not a transcript and must not become a report. " * 8
    )
    destination = tmp_path / "from-recap.md"
    result = write_report(
        transcript=TranscriptResult("found", text=recap, source_kind="recap"),
        destination=destination,
        title="Recap only",
    )
    assert result.written is False
    assert destination.exists() is False
    assert "Refusing" in (result.reason or "")


def test_report_shape_has_header_main_points_and_caveats():
    markdown = build_report_markdown(
        transcript_text=FIXTURE.read_text(encoding="utf-8"),
        title="Fixture interview",
        show_name="Fixture show",
        published="2026-08-01",
        url="https://example.test/fixture",
        duration_minutes=60,
        guest_hint="Guest Speaker",
        transcript_source="fixture",
    )
    assert "# Fixture interview" in markdown
    assert "## Main points" in markdown
    assert "## Caveats and disagreements" in markdown
    assert "12 dollars per million tokens" in markdown
