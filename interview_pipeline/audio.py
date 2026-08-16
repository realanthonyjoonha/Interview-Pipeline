from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from interview_pipeline.http import HttpError, fetch_to_file
from interview_pipeline.models import Episode, TranscriptResult
from interview_pipeline.paths import repo_root


class TranscriptionError(RuntimeError):
    pass


def find_whisper_bin(explicit: str | None = None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env = os.environ.get("WHISPER_BIN")
    if env:
        candidates.append(Path(env))
    root = repo_root()
    candidates.extend(
        [
            root / "tools" / "whisper" / "whisper-cli",
            root / "tools" / "whisper" / "main",
        ]
    )
    for name in ("whisper-cli", "whisper", "main"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for path in candidates:
        if path.is_file() and os.access(path, os.X_OK):
            return path
    return None


def find_whisper_model(explicit: str | None = None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env = os.environ.get("WHISPER_MODEL")
    if env:
        candidates.append(Path(env))
    root = repo_root()
    tools = root / "tools" / "whisper"
    if tools.is_dir():
        candidates.extend(sorted(tools.glob("ggml-*.bin")))
    for path in candidates:
        if path.is_file() and path.stat().st_size > 1000:
            return path
    return None


def download_audio(url: str, destination: Path) -> Path:
    return fetch_to_file(url, destination, timeout=300)


def to_wav_16k(source: Path, destination: Path) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise TranscriptionError("ffmpeg is required to convert episode audio to 16 kHz WAV")
    destination.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or exc.stdout or str(exc))[-400:]
        raise TranscriptionError(f"ffmpeg failed: {err}") from exc
    if not destination.is_file() or destination.stat().st_size < 100:
        raise TranscriptionError("ffmpeg produced an empty or tiny WAV")
    return destination


def _parse_whisper_srt(srt_text: str) -> str:
    blocks = re.split(r"\n\s*\n", srt_text.strip())
    lines: list[str] = []
    for block in blocks:
        parts = [p.strip() for p in block.splitlines() if p.strip()]
        if len(parts) < 2:
            continue
        stamp = ""
        text_parts: list[str] = []
        for part in parts:
            if re.match(r"^\d+$", part):
                continue
            match = re.match(
                r"(\d{2}:\d{2}:\d{2})[,\.]\d+\s+-->\s+(\d{2}:\d{2}:\d{2})",
                part,
            )
            if match:
                stamp = match.group(1)
                continue
            text_parts.append(part)
        body = " ".join(text_parts).strip()
        if not body:
            continue
        if stamp:
            lines.append(f"[{stamp}] Speaker: {body}")
        else:
            lines.append(f"Speaker: {body}")
    return "\n\n".join(lines)


def _parse_whisper_txt(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    # whisper.cpp sometimes prefixes [00:00:00.000 --> 00:00:04.000]
    stamped = re.findall(
        r"\[(\d{2}:\d{2}:\d{2})(?:\.\d+)?\s*-->\s*[^\]]+\]\s*(.+)",
        cleaned,
    )
    if stamped:
        return "\n\n".join(f"[{start}] Speaker: {body.strip()}" for start, body in stamped if body.strip())
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    if len(paragraphs) == 1:
        sentences = re.split(r"(?<=[.!?])\s+", paragraphs[0])
        paragraphs = [s.strip() for s in sentences if s.strip()]
    return "\n\n".join(f"Speaker: {p}" for p in paragraphs)


def transcribe_wav(
    wav_path: Path,
    *,
    whisper_bin: Path | None = None,
    whisper_model: Path | None = None,
    work_dir: Path | None = None,
) -> str:
    if not wav_path.is_file() or wav_path.stat().st_size < 100:
        raise TranscriptionError("audio file is empty or missing")
    binary = find_whisper_bin(str(whisper_bin) if whisper_bin else None)
    model = find_whisper_model(str(whisper_model) if whisper_model else None)
    if binary is None or model is None:
        raise TranscriptionError(
            "whisper.cpp is not installed. Run scripts/bootstrap-whisper.sh "
            "or set WHISPER_BIN and WHISPER_MODEL. See README."
        )
    out_dir = work_dir or wav_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / wav_path.stem
    cmd = [
        str(binary),
        "-m",
        str(model),
        "-f",
        str(wav_path),
        "-osrt",
        "-otxt",
        "-of",
        str(prefix),
        "-l",
        "en",
        "-nt",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=6 * 60 * 60)
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or exc.stdout or str(exc))[-500:]
        raise TranscriptionError(f"whisper.cpp failed: {err}") from exc
    except subprocess.TimeoutExpired as exc:
        raise TranscriptionError("whisper.cpp timed out") from exc

    srt = Path(str(prefix) + ".srt")
    txt = Path(str(prefix) + ".txt")
    if srt.is_file():
        parsed = _parse_whisper_srt(srt.read_text(encoding="utf-8", errors="replace"))
        if parsed.strip():
            return parsed
    if txt.is_file():
        parsed = _parse_whisper_txt(txt.read_text(encoding="utf-8", errors="replace"))
        if parsed.strip():
            return parsed
    raise TranscriptionError("whisper.cpp produced no usable text")


def transcribe_episode_audio(
    episode: Episode,
    *,
    work_dir: Path,
    download_fn=None,
    transcribe_fn=None,
    whisper_bin: str | None = None,
    whisper_model: str | None = None,
) -> TranscriptResult:
    if not episode.audio_url:
        return TranscriptResult(
            "missing",
            source_url=episode.url or None,
            source_kind="audio_whisper",
            detail="No official transcript and no RSS audio enclosure",
            derived_from_audio=False,
        )
    work_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(episode.audio_url.split("?", 1)[0]).suffix or ".mp3"
    if suffix.lower() not in {".mp3", ".m4a", ".wav", ".mp4", ".aac", ".ogg"}:
        suffix = ".mp3"
    raw_path = work_dir / f"{episode.slug}{suffix}"
    wav_path = work_dir / f"{episode.slug}.wav"
    try:
        downloader = download_fn or download_audio
        downloader(episode.audio_url, raw_path)
        if raw_path.stat().st_size < 100:
            return TranscriptResult(
                "error",
                source_url=episode.audio_url,
                source_kind="audio_whisper",
                detail="Downloaded audio is empty",
                derived_from_audio=True,
            )
        if transcribe_fn is not None:
            text = transcribe_fn(raw_path)
        else:
            to_wav_16k(raw_path, wav_path)
            text = transcribe_wav(
                wav_path,
                whisper_bin=Path(whisper_bin) if whisper_bin else None,
                whisper_model=Path(whisper_model) if whisper_model else None,
                work_dir=work_dir,
            )
    except (HttpError, TranscriptionError, OSError) as exc:
        return TranscriptResult(
            "error",
            source_url=episode.audio_url,
            source_kind="audio_whisper",
            detail=str(exc),
            derived_from_audio=True,
        )
    if not text or not str(text).strip():
        return TranscriptResult(
            "error",
            source_url=episode.audio_url,
            source_kind="audio_whisper",
            detail="Audio transcription returned empty text",
            derived_from_audio=True,
        )
    return TranscriptResult(
        "found",
        text=str(text).strip(),
        source_url=episode.audio_url,
        source_kind="audio_whisper",
        detail="Local whisper.cpp transcript from the RSS audio enclosure. Not official-page quotes.",
        derived_from_audio=True,
    )
