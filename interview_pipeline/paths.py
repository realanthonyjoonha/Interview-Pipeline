from __future__ import annotations

from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    candidates = []
    if start is not None:
        candidates.append(start)
    here = Path(__file__).resolve()
    candidates.extend([here.parent, here.parent.parent, Path.cwd()])
    for path in candidates:
        if (path / "config" / "shows.json").exists():
            return path
        if (path / "pyproject.toml").exists() and (path / "interview_pipeline").exists():
            return path
    return Path.cwd()


def data_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "data"
