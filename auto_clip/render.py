from __future__ import annotations

from pathlib import Path

from auto_clip.config import PipelineConfig
from auto_clip.types import DropCandidate
from auto_clip.utils import run_command


def render_clips(
    video_path: str,
    source_id: str,
    candidates: list[DropCandidate],
    config: PipelineConfig,
) -> list[dict[str, str | float]]:
    output_root = Path(config.output_dir) / source_id
    output_root.mkdir(parents=True, exist_ok=True)

    # Render best-scoring moments first: clip_01 is always the strongest drop.
    ordered = sorted(candidates, key=lambda c: c.score, reverse=True)

    manifest: list[dict[str, str | float]] = []
    for index, candidate in enumerate(ordered, start=1):
        start_seconds = max(0.0, candidate.timestamp_seconds - float(config.pre_drop_seconds))
        output_file = output_root / f"clip_{index:02d}_{int(candidate.timestamp_seconds):05d}.mp4"
        command = build_ffmpeg_command(
            video_path=video_path,
            output_path=str(output_file),
            start_seconds=start_seconds,
            duration_seconds=float(config.clip_duration_seconds),
            vertical=config.render_vertical_9x16,
            vertical_mode=config.vertical_mode,
        )
        run_command(command, dry_run=config.dry_run)

        manifest.append(
            {
                "clip_path": str(output_file),
                "drop_timestamp_seconds": candidate.timestamp_seconds,
                "score": candidate.score,
                "start_seconds": start_seconds,
                "duration_seconds": float(config.clip_duration_seconds),
            }
        )

    return manifest


def build_ffmpeg_command(
    video_path: str,
    output_path: str,
    start_seconds: float,
    duration_seconds: float,
    vertical: bool,
    vertical_mode: str = "crop",
) -> list[str]:
    if not vertical:
        return [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start_seconds:.3f}",
            "-i",
            video_path,
            "-t",
            f"{duration_seconds:.3f}",
            "-c",
            "copy",
            output_path,
        ]

    if vertical_mode == "crop":
        # Center-crop to 9:16 (fills the vertical frame, crops the sides).
        return [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start_seconds:.3f}",
            "-i",
            video_path,
            "-t",
            f"{duration_seconds:.3f}",
            "-vf",
            "crop=ih*9/16:ih,scale=1080:1920,setsar=1",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            output_path,
        ]

    filter_graph = (
        "[0:v]scale=1080:-2,split=2[fg][bg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,boxblur=20:2,crop=1080:1920[bg2];"
        "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg2];"
        "[bg2][fg2]overlay=(W-w)/2:(H-h)/2"
    )

    return [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start_seconds:.3f}",
        "-i",
        video_path,
        "-t",
        f"{duration_seconds:.3f}",
        "-filter_complex",
        filter_graph,
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "21",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        output_path,
    ]
