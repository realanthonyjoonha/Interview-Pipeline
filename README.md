# Interview-Pipeline

Scan a locked set of long-form interview shows, keep structured episode records, fetch an **official** transcript when one is public, and write extractive main-points notes. The chat agent stays the editor. This repo does the fetch and first draft so a conversation does not burn tokens re-pulling transcripts.

This is **not** Cockpit. Notes are decision-support / time-saving only. No house view. No buy/sell. No investment-desk framing. If there is no official transcript, the pipeline records that fact and **does not write a report**. It does not invent quotes or write from recaps.

## What v1 does

1. Ingests official RSS feeds for the CORE shows (and optional secondary shows if you enable them).
2. Applies the show filters (interview vs essay, guest sit, length bar, topic gates).
3. Fetches an official transcript when the show publishes one (RSS `podcast:transcript`, public Substack transcript, or a public Lex `-transcript` page).
4. Marks paywalled / login-gated transcripts instead of scraping around them (Lenny paid posts, Colossus/ILTB unless the transcript is on the public page).
5. If a real transcript exists, writes a markdown note: header, attributed main points, numbers, caveats.
6. Saves artifacts under `data/`.

No paid API keys are required. Optional keys are not used.

## Locked people

Do not add names to this list. The pipeline only flags mentions; it does not expand the set.

Sam Altman, Dario Amodei, Demis Hassabis, Elon Musk, Satya Nadella, Sundar Pichai, Mark Zuckerberg, Jensen Huang, Ilya Sutskever, Andrej Karpathy.

## CORE shows

| Show | Filter | Official transcript in v1 |
| --- | --- | --- |
| Dwarkesh Podcast | Interviews only; skip sub-20 min essays | Public Substack transcript section |
| Cheeky Pint | Founder sits; quiet since 27 Apr 2026 | RSS `podcast:transcript` |
| No Priors | Guest sit or 45+; skip host-only under 45 | Usually none → record missing |
| BG2 | Irregular; 45+ min bar | Usually none → record missing |
| Big Technology | Named guest interviews; skip news roundtables | Usually none → record missing |
| Invest Like the Best | AI / infra / chip / lab guests only | Colossus treated as login-gated unless public |
| SemiAnalysis Weekly | Staff semis/infra analysis, not a figurehead hunt | Usually none → record missing |
| Latent Space | Long interviews only; ignore AINews shorts | Public Substack player transcript |
| The Pragmatic Engineer | Enterprise / dev-tool adoption interviews | Public Substack player transcript |
| Lenny’s Podcast | Only when guest/title is AI-product | Paid posts marked paywalled |

Length bar: about 45+ minutes, except SemiAnalysis Weekly shorts about China silicon, InferenceX, or a named teardown.

Secondary shows (Lex Fridman, Decoder, Possible, Training Data, 20VC, Hard Fork, Practical AI, Stratechery Interview, Conversations with Tyler) live in `config/shows.json` with `"enabled": false`. Add a feed URL and flip the flag to include them.

## Setup

Python 3.11+. No third-party runtime dependencies.

```bash
python3 -m pip install -e '.[dev]'   # pytest only, for tests
# or just run from the repo root:
python3 -m interview_pipeline --help
```

## Run one local scan

From the repo root:

```bash
# List CORE shows
python3 -m interview_pipeline shows

# Scan 2–3 CORE shows, last 3 weeks, write episode records + transcripts + reports
python3 -m interview_pipeline scan --show dwarkesh --limit 8 --max-matches 2
python3 -m interview_pipeline scan --show cheeky_pint --limit 8 --max-matches 2
python3 -m interview_pipeline scan --show latent_space --limit 8 --max-matches 2

# Or all enabled CORE shows
python3 -m interview_pipeline scan --tier core --since 21 --limit 8 --max-matches 2
```

Episode JSON always gets written. A report is written only when an official transcript was fetched and parsed into speaker turns.

Write a report from a local official transcript (or the test fixture):

```bash
python3 -m interview_pipeline report \
  --transcript tests/fixtures/sample_transcript.md \
  --out /tmp/fixture-report.md \
  --title "Fixture interview" \
  --show-name "Fixture show"
```

If you pass an empty file or a recap with no speaker turns, the command exits 2 and writes nothing.

## Weekday job

A weekday cron / GitHub Action should do a bounded CORE scan, then a human or chat editor reviews new reports.

```bash
# Weekdays 08:00 local: last 8 days, up to 3 matches per show
0 8 * * 1-5 cd /path/to/Interview-Pipeline && python3 -m interview_pipeline scan --tier core --since 8 --limit 12 --max-matches 3
```

Still manual after the job:

- Edit the extractive note (the chat agent is the editor).
- Skip or mark shows whose official transcript is paywalled.
- Commit new `data/` artifacts if you want them in git.
- Enable secondary shows in `config/shows.json` when you want them.

## Artifact layout

```
config/shows.json              # show list, filters, locked people
data/episodes/<show>/<slug>.json
data/transcripts/<show>/<slug>.md
data/reports/<show>/<slug>.md
data/scans/<timestamp>.json
```

Reports are extractive: they quote or tightly excerpt speaker turns from the official transcript. They are not a house view.

## Tests

```bash
python3 -m pytest -q
```

Covered in v1: show filter rules, and **no transcript ⇒ no report**.

## What is still manual

- Reviewing and tightening reports (this repo drafts; it does not publish a desk view).
- Shows without a public official transcript: the scan records `transcript.status = missing` and stops.
- Paywalled Lenny posts and login-gated Colossus pages: marked, not scraped.
- Some public Substack player transcripts use `SPEAKER_01` labels; do not rename them unless the official page does.
- Secondary feeds that are blank in `config/shows.json` need an official RSS URL before they can be enabled.
