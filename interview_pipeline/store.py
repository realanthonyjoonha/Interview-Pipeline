from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from interview_pipeline.models import Episode
from interview_pipeline.paths import data_dir, repo_root


def episode_paths(episode: Episode, root: Path | None = None) -> dict[str, Path]:
    base = data_dir(root or repo_root())
    slug = episode.slug
    show = episode.show_id
    return {
        "episode": base / "episodes" / show / f"{slug}.json",
        "transcript": base / "transcripts" / show / f"{slug}.md",
        "report": base / "reports" / show / f"{slug}.md",
    }


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_scan_summary(rows: list[dict], root: Path | None = None) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = data_dir(root or repo_root()) / "scans" / f"{stamp}.json"
    write_json(
        path,
        {
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "episode_count": len(rows),
            "matched": sum(1 for row in rows if (row.get("filter") or {}).get("matched")),
            "transcripts_found": sum(
                1 for row in rows if (row.get("transcript") or {}).get("status") == "found"
            ),
            "reports_written": sum(1 for row in rows if (row.get("report") or {}).get("written")),
            "episodes": rows,
        },
    )
    return path
