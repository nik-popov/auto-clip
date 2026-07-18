from __future__ import annotations

from pathlib import Path

from auto_clip.config import PipelineConfig
from auto_clip.types import SourceArtifacts
from auto_clip.utils import run_command, stable_source_id


def _is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


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
            run_command(
                [
                    "yt-dlp",
                    "-f",
                    "bv*[height<=1080]+ba/b[height<=1080]/b",
                    "--merge-output-format",
                    "mp4",
                    "-o",
                    str(video_path),
                    source,
                ],
                dry_run=config.dry_run,
            )
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
