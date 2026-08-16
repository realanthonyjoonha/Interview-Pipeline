from interview_pipeline.feeds import parse_duration_seconds, parse_rss
from interview_pipeline.models import Show
from interview_pipeline.transcripts import (
    extract_substack_body_transcript,
    is_speaker_name,
    looks_like_transcript,
    parse_cheeky_transcript,
    substack_segments_to_text,
)

SHOW = Show(
    id="dwarkesh",
    name="Dwarkesh Podcast",
    tier="core",
    enabled=True,
    feed_url="https://example.test/feed",
    site="",
    transcript="substack",
    filter="dwarkesh",
)


def test_parse_duration_seconds():
    assert parse_duration_seconds("7952") == 7952
    assert parse_duration_seconds("01:20:47") == 1 * 3600 + 20 * 60 + 47
    assert parse_duration_seconds("50:03") == 50 * 60 + 3
    assert parse_duration_seconds("") is None
    assert parse_duration_seconds(None) is None


def test_parse_rss_fixture():
    from pathlib import Path

    feed = Path(__file__).parent / "fixtures" / "sample_feed.xml"
    episodes = parse_rss(feed.read_text(encoding="utf-8"), SHOW)
    assert len(episodes) == 2
    assert episodes[0].title.startswith("Ryan Guest")
    assert episodes[0].duration_seconds == 7952
    assert episodes[0].published == "2026-08-11"
    assert episodes[1].duration_seconds == 517


def test_parse_cheeky_transcript_to_speaker_turns():
    raw = """[00:00:02.10] Evan Spiegel
This is pretty funny playing chess in the pub.

[00:00:09.14] John Collison
Give me the Snap 2026 update: product, business.
"""
    text = parse_cheeky_transcript(raw)
    assert "Evan Spiegel: This is pretty funny" in text
    assert "John Collison: Give me the Snap 2026 update" in text
    assert looks_like_transcript(text + "\n\nEvan Spiegel: " + ("more words " * 40) + "\n\nJohn Collison: " + ("reply " * 40))


def test_extract_substack_body_transcript():
    html = """
    <h3><strong>Timestamps</strong></h3>
    <p>00:00 intro</p>
    <h3><strong>Transcript</strong></h3>
    <p><strong>Dwarkesh Patel</strong></p>
    <p>Today I am chatting with a guest about recursive self-improvement and data bottlenecks.</p>
    <p><strong>Ryan Greenblatt</strong></p>
    <p>My median for automating AI R and D is 2031, with a wide confidence interval.</p>
    <p><strong>Dwarkesh Patel</strong></p>
    <p>That is a concrete number and I want to sit with the caveat that it is a median.</p>
    <p><strong>Ryan Greenblatt</strong></p>
    <p>Yes, treat it as a median, not a point forecast.</p>
    """
    text = extract_substack_body_transcript(html)
    assert text is not None
    assert "Dwarkesh Patel:" in text
    assert "2031" in text


def test_speaker_name_rejects_sentence_fragments():
    assert is_speaker_name("Ryan Greenblatt") is True
    assert is_speaker_name("Dwarkesh Patel") is True
    assert is_speaker_name("Host") is True
    assert is_speaker_name("That makes sense.") is False
    assert is_speaker_name("Interesting.") is False
    assert is_speaker_name("Partially.") is False
    assert is_speaker_name("Pretty high.") is False


def test_substack_segments_to_text():
    segments = [
        {
            "text": "Why are there two camps?",
            "words": [{"speaker": "SPEAKER_01", "word": "Why"}],
        },
        {
            "text": "Because the tools changed.",
            "words": [{"speaker": "SPEAKER_02", "word": "Because"}],
        },
        {
            "text": "That is the whole argument.",
            "words": [{"speaker": "SPEAKER_02", "word": "That"}],
        },
    ]
    text = substack_segments_to_text(segments)
    assert text.startswith("SPEAKER_01: Why are there two camps?")
    assert "SPEAKER_02: Because the tools changed. That is the whole argument." in text
