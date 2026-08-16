# Interview-Pipeline

Scan a locked set of long-form interview shows, keep structured episode records, fetch an **official** transcript when one is public, and otherwise transcribe the RSS audio locally. Then write an extractive main-points brief. The chat agent stays the editor.

This is **not** Cockpit. Notes are decision-support / time-saving only. No house view. No buy/sell. No investment-desk framing. Do not invent quotes. Do not write from recaps. If there is no official text **and** audio transcription fails or there is no audio, the pipeline records that fact and **does not write a report**.

## What v1 does

1. Ingests official RSS feeds for the CORE shows (and optional secondary shows if you enable them).
2. Applies the show filters (interview vs essay, guest sit, length bar, topic gates).
3. Prefers an official public transcript (RSS `podcast:transcript`, public Substack transcript, public Lex `-transcript` page).
4. If official text is missing, paywalled, or login-gated, downloads the RSS audio enclosure and transcribes it locally with **whisper.cpp**. Those reports are marked **audio-derived**, not official-page quotes.
5. Does **not** scrape login-gated Colossus pages. Audio transcription is the allowed fallback.
6. Writes a grouped markdown brief: arguments, numbers they stated, caveats, disagreements. Not a quote dump.
7. Saves artifacts under `data/`.

No paid API keys are required.

## Locked people

Do not add names to this list. The pipeline only flags mentions; it does not expand the set.

Sam Altman, Dario Amodei, Demis Hassabis, Elon Musk, Satya Nadella, Sundar Pichai, Mark Zuckerberg, Jensen Huang, Ilya Sutskever, Andrej Karpathy.

## CORE shows

| Show | Filter | Transcript in v1 |
| --- | --- | --- |
| Dwarkesh Podcast | Interviews only; skip sub-20 min essays | Official Substack page, else audio |
| Cheeky Pint | Founder sits; quiet since 27 Apr 2026 | Official RSS transcript, else audio |
| No Priors | Guest sit or 20+; skip host-only under 20 | Usually audio-derived |
| BG2 | Irregular; 20+ min bar | Usually audio-derived |
| Big Technology | Named guest interviews; skip news roundtables | Usually audio-derived |
| Invest Like the Best | AI / infra / chip / lab guests only | Colossus not scraped; audio fallback |
| SemiAnalysis Weekly | Staff semis/infra analysis, not a figurehead hunt | Usually audio-derived |
| Latent Space | Long interviews only; ignore AINews shorts | Official Substack, else audio |
| The Pragmatic Engineer | Enterprise / dev-tool adoption interviews | Official Substack, else audio |
| Lenny’s Podcast | Only when guest/title is AI-product | Paid posts → audio fallback |

Length bar: **20+ minutes**. A 25-minute in-scope sit is a match. SemiAnalysis Weekly numbered episodes count at 20+; the short-teardown exception still applies for China silicon, InferenceX, or a named teardown.

Secondary shows live in `config/shows.json` with `"enabled": false`.

## Setup

Python 3.11+. Runtime code has no PyPI dependencies. Audio fallback needs **ffmpeg** and **whisper.cpp**.

```bash
python3 -m pip install -e '.[dev]'   # pytest only, for tests
sudo apt-get install -y ffmpeg       # if it is not already on PATH

# Local whisper.cpp CLI + tiny.en model (no API key)
./scripts/bootstrap-whisper.sh
# or set:
#   export WHISPER_BIN=/path/to/whisper-cli
#   export WHISPER_MODEL=/path/to/ggml-tiny.en.bin
```

`bootstrap-whisper.sh` downloads the official whisper.cpp Ubuntu x64 release and `ggml-tiny.en.bin` into `tools/whisper/` (gitignored). Larger models (`base.en`, `small.en`) are more accurate if you point `WHISPER_MODEL` at them.

Without whisper.cpp, official-transcript shows still scan. Shows with no public text will record `transcript.status = missing` or `error` and will not invent a report.

## Run one local scan

```bash
python3 -m interview_pipeline shows

# Official-transcript shows
python3 -m interview_pipeline scan --show dwarkesh --limit 8 --max-matches 2

# Audio-fallback shows (No Priors / BG2 / SemiAnalysis Weekly)
python3 -m interview_pipeline scan --show no_priors --since 30 --limit 6 --max-matches 1

# Skip the audio fallback
python3 -m interview_pipeline scan --show no_priors --skip-audio

# All enabled CORE shows
python3 -m interview_pipeline scan --tier core --since 21 --limit 8 --max-matches 2
```

A report is written only when a usable official or audio-derived transcript was obtained. A checked-in example is `data/reports/no_priors/2026-08-13-what-chess-com-teaches-us-about-superhuman-capabilities-with-ceo-erik-allebest.md` (audio-derived from whisper.cpp after the official page was missing).

```bash
python3 -m interview_pipeline report \
  --transcript tests/fixtures/sample_transcript.md \
  --out /tmp/fixture-report.md \
  --title "Fixture interview" \
  --show-name "Fixture show"
```

Empty files, recaps, empty audio, and failed transcriptions exit 2 and write nothing.

## Weekday job

```bash
# Once per machine
./scripts/bootstrap-whisper.sh

# Weekdays 08:00: last 8 days, up to 3 matches per show (official first, then audio)
0 8 * * 1-5 cd /path/to/Interview-Pipeline && python3 -m interview_pipeline scan --tier core --since 8 --limit 12 --max-matches 3
```

Still manual after the job: edit the brief, commit new `data/` artifacts if you want them in git, enable secondary shows.

## Artifact layout

```
config/shows.json
data/episodes/<show>/<slug>.json
data/transcripts/<show>/<slug>.md
data/reports/<show>/<slug>.md
data/audio/<show>/          # downloaded enclosures + wav (gitignored)
data/scans/<timestamp>.json
tools/whisper/              # local whisper.cpp + model (gitignored)
```

Audio-derived reports say so in the header. Official-page transcripts remain the preferred source.

## Tests

```bash
python3 -m pytest -q
```

Covered: show filters; official text preferred; missing official + fixture audio path still writes an audio-derived report; empty audio / failed transcription / no audio ⇒ no report; Colossus is not scraped.

## What is still manual

- Reviewing and tightening briefs (this repo drafts; it does not publish a desk view).
- whisper.cpp speaker labels are often generic (`Speaker`). Do not invent names.
- Choosing a larger Whisper model if tiny.en is too rough.
- Enabling secondary shows and filling blank feed URLs.
