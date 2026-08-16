from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from interview_pipeline.models import Show
from interview_pipeline.paths import repo_root


@lru_cache(maxsize=4)
def load_catalog(path: str | None = None) -> dict:
    catalog_path = Path(path) if path else repo_root() / "config" / "shows.json"
    with catalog_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def watched_people(catalog: dict | None = None) -> tuple[str, ...]:
    data = catalog or load_catalog()
    return tuple(data.get("watched_people") or ())


def default_min_minutes(catalog: dict | None = None) -> int:
    data = catalog or load_catalog()
    return int((data.get("defaults") or {}).get("min_minutes") or 20)


def user_agent(catalog: dict | None = None) -> str:
    data = catalog or load_catalog()
    return str(
        (data.get("defaults") or {}).get("user_agent")
        or "InterviewPipeline/0.1 (+research notes)"
    )


def shows(
    *,
    catalog: dict | None = None,
    tier: str | None = None,
    enabled_only: bool = True,
    show_id: str | None = None,
) -> list[Show]:
    data = catalog or load_catalog()
    out: list[Show] = []
    for raw in data.get("shows") or []:
        show = Show(
            id=raw["id"],
            name=raw["name"],
            tier=raw.get("tier") or "secondary",
            enabled=bool(raw.get("enabled")),
            feed_url=raw.get("feed_url") or "",
            site=raw.get("site") or "",
            transcript=raw.get("transcript") or "none_known",
            filter=raw.get("filter") or "length_only",
            notes=raw.get("notes") or "",
            hosts=tuple(raw.get("hosts") or ()),
        )
        if show_id and show.id != show_id:
            continue
        if enabled_only and not show.enabled:
            continue
        if tier and show.tier != tier:
            continue
        out.append(show)
    return out
