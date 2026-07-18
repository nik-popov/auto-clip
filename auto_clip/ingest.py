from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path

from auto_clip.config import PipelineConfig
from auto_clip.types import SourceArtifacts
from auto_clip.utils import run_command, stable_source_id


def _is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _download_with_ytdlp(source: str, video_path: Path, config: PipelineConfig) -> None:
    base = [
        "yt-dlp",
        "-f",
        "bv*[height<=1080]+ba/b[height<=1080]/b",
        "--merge-output-format",
        "mp4",
        "--no-warnings",
        "-o",
        str(video_path),
    ]

    proxy = os.environ.get("YTDLP_PROXY", "").strip()
    if proxy:
        base += ["--proxy", proxy]

    cookies_b64 = os.environ.get("YTDLP_COOKIES_B64", "").strip()
    if cookies_b64:
        cookies_path = video_path.parent / "cookies.txt"
        try:
            cookies_path.write_bytes(base64.b64decode(cookies_b64))
            base += ["--cookies", str(cookies_path)]
        except Exception:
            pass

    if config.dry_run:
        print("[dry-run]", " ".join(base + [source]))
        return

    is_youtube = "youtube.com" in source or "youtu.be" in source
    attempts: list[list[str]] = [[]]
    if is_youtube:
        attempts += [
            ["--extractor-args", "youtube:player_client=tv"],
            ["--extractor-args", "youtube:player_client=ios"],
        ]

    last_error = "unknown error"
    for extra in attempts:
        result = subprocess.run(base + extra + [source], capture_output=True, text=True)
        if result.returncode == 0 and video_path.exists():
            return
        stderr_tail = (result.stderr or "").strip()[-600:]
        if stderr_tail:
            last_error = stderr_tail

    raise RuntimeError(f"Video download failed after {len(attempts)} attempt(s): {last_error}")


def ingest_source(source: str, work_dir: str, config: PipelineConfig) -> SourceArtifacts:
    source_id = stable_source_id(source)
    source_dir = Path(work_dir) / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    video_path = source_dir / "source.mp4"
    wav_path = source_dir / "source.wav"

    if _is_url(source):
        direct_extensions = (".mp4", ".mkv", ".webm", ".mov", ".m4v", ".mp3", ".wav")
        path_part = source.split("?", 1)[0].lower()
        if path_part.endswith(direct_extensions):
            run_command(
                ["curl", "-L", "--fail", "-sS", "-o", str(video_path), source],
                dry_run=config.dry_run,
            )
        else:
            _download_with_ytdlp(source, video_path, config)
    else:
        original = Path(source)
        if not original.exists() and not config.dry_run:
            raise FileNotFoundError(f"Source file not found: {original}")
        if not config.dry_run:
            video_path.write_bytes(original.read_bytes())

    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-ac",
            "1",
            "-ar",
            str(config.sample_rate),
            str(wav_path),
        ],
        dry_run=config.dry_run,
    )

    return SourceArtifacts(
        source_id=source_id,
        video_path=str(video_path),
        wav_path=str(wav_path),
    )
