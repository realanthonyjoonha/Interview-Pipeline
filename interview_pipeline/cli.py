from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from interview_pipeline.catalog import shows
from interview_pipeline.feeds import fetch_episodes
from interview_pipeline.filters import decide
from interview_pipeline.models import Episode, TranscriptResult, episode_record
from interview_pipeline.paths import repo_root
from interview_pipeline.reports import write_report
from interview_pipeline.resolve import resolve_transcript
from interview_pipeline.store import episode_paths, write_json, write_scan_summary, write_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="interview-pipeline",
        description="Scan CORE interview shows, fetch official transcripts, write main-points notes.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    scan = sub.add_parser("scan", help="Fetch RSS, filter episodes, optionally fetch transcripts and write reports")
    scan.add_argument("--show", dest="show_id", help="Show id from config/shows.json")
    scan.add_argument("--tier", choices=("core", "secondary"), default="core")
    scan.add_argument("--limit", type=int, default=8, help="Max RSS items to consider per show")
    scan.add_argument("--since", type=int, default=21, help="Only episodes published in the last N days (0 = all)")
    scan.add_argument("--max-matches", type=int, default=3, help="Max matching episodes to process per show")
    scan.add_argument("--skip-transcripts", action="store_true")
    scan.add_argument("--skip-audio", action="store_true", help="Do not fall back to local audio transcription")
    scan.add_argument("--no-report", action="store_true")
    scan.add_argument("--include-disabled", action="store_true")
    scan.add_argument("--whisper-bin", default=None)
    scan.add_argument("--whisper-model", default=None)
    scan.add_argument("--root", type=Path, default=None)

    report = sub.add_parser("report", help="Write a report from a local official transcript file")
    report.add_argument("--transcript", required=True, type=Path)
    report.add_argument("--out", type=Path, required=True)
    report.add_argument("--title", default="Fixture episode")
    report.add_argument("--show-name", default="Fixture show")
    report.add_argument("--published", default="")
    report.add_argument("--url", default="")

    listing = sub.add_parser("shows", help="List configured shows")
    listing.add_argument("--all", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd == "shows":
        return _cmd_shows(all_shows=args.all)
    if args.cmd == "report":
        return _cmd_report(args)
    return _cmd_scan(args)


def _cmd_shows(*, all_shows: bool) -> int:
    rows = shows(enabled_only=not all_shows) if not all_shows else shows(enabled_only=False)
    for show in rows:
        flag = "on " if show.enabled else "off"
        print(f"{show.id:28} {flag} {show.tier:10} {show.name}")
        if show.notes:
            print(f"  {show.notes}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    text = args.transcript.read_text(encoding="utf-8")
    episode = Episode(
        show_id="fixture",
        show_name=args.show_name,
        title=args.title,
        published=args.published,
        url=args.url,
        guid=str(args.transcript),
        duration_seconds=None,
    )
    result = write_report(
        transcript=TranscriptResult("found", text=text, source_url=str(args.transcript), source_kind="local_file"),
        destination=args.out,
        episode=episode,
        title=args.title,
        show_name=args.show_name,
    )
    if not result.written:
        print(result.reason, file=sys.stderr)
        return 2
    print(result.path)
    return 0


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _parse_since(published: str, since_days: int) -> bool:
    if since_days <= 0 or not published:
        return True
    try:
        day = date.fromisoformat(published[:10])
    except ValueError:
        return True
    return day >= (datetime.now().date() - timedelta(days=since_days))


def _cmd_scan(args: argparse.Namespace) -> int:
    root = args.root or repo_root()
    selected = shows(
        show_id=args.show_id,
        tier=None if args.show_id else args.tier,
        enabled_only=not args.include_disabled,
    )
    if not selected:
        print("No shows selected. Check --show / --tier / enabled flags.", file=sys.stderr)
        return 2

    rows: list[dict] = []
    for show in selected:
        print(f"\n== {show.name} ({show.id}) ==")
        if not show.feed_url:
            print("  skipped: no feed_url configured")
            continue
        try:
            episodes = fetch_episodes(show)
        except Exception as exc:  # noqa: BLE001 - CLI should keep scanning other shows
            print(f"  feed error: {exc}", file=sys.stderr)
            continue

        considered = 0
        matched = 0
        for episode in episodes:
            if considered >= args.limit:
                break
            if not _parse_since(episode.published, args.since):
                continue
            considered += 1
            decision = decide(episode, show)
            paths = episode_paths(episode, root)
            rec = episode_record(episode, decision)
            rec["paths"] = {key: _rel(path, root) for key, path in paths.items()}

            if not decision.matched:
                print(f"  skip  {episode.published}  {episode.title[:90]}")
                for reason in decision.reasons:
                    print(f"         {reason}")
                write_json(paths["episode"], rec)
                rows.append(rec)
                continue

            matched += 1
            print(f"  match {episode.published}  {episode.title[:90]}")
            for reason in decision.reasons:
                print(f"         {reason}")

            transcript = None
            report = None
            if not args.skip_transcripts:
                audio_dir = root / "data" / "audio" / episode.show_id
                transcript = resolve_transcript(
                    episode,
                    show,
                    work_dir=audio_dir,
                    skip_audio=args.skip_audio,
                    whisper_bin=args.whisper_bin,
                    whisper_model=args.whisper_model,
                )
                rec = episode_record(episode, decision, transcript=transcript)
                rec["paths"] = {key: _rel(path, root) for key, path in paths.items()}
                kind = "audio-derived" if transcript.derived_from_audio else "official"
                print(
                    f"         transcript: {transcript.status} [{kind}] "
                    f"({transcript.detail or transcript.source_kind})"
                )
                if transcript.found and transcript.text:
                    write_text(paths["transcript"], transcript.text)
                    rec["transcript"]["path"] = _rel(paths["transcript"], root)
                if args.no_report:
                    pass
                else:
                    report = write_report(
                        transcript=transcript,
                        destination=paths["report"],
                        episode=episode,
                        guest_hint=decision.guest_hint,
                    )
                    rec["report"] = {
                        "written": report.written,
                        "path": _rel(Path(report.path), root) if report.path else None,
                        "reason": report.reason,
                    }
                    if report.written:
                        print(f"         report: wrote {report.path}")
                    else:
                        print(f"         report: {report.reason}")

            write_json(paths["episode"], rec)
            rows.append(rec)
            if matched >= args.max_matches:
                break

    summary = write_scan_summary(rows, root)
    print(f"\nWrote {len(rows)} episode records. Scan summary: {summary}")
    print(json.dumps({
        "episodes": len(rows),
        "matched": sum(1 for row in rows if row.get("filter", {}).get("matched")),
        "transcripts_found": sum(1 for row in rows if (row.get("transcript") or {}).get("status") == "found"),
        "reports_written": sum(1 for row in rows if (row.get("report") or {}).get("written")),
    }, indent=2))
    return 0
