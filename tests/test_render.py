from auto_clip.render import build_ffmpeg_command, render_clips
from auto_clip.config import PipelineConfig
from auto_clip.types import DropCandidate


def test_render_clips_orders_by_score(tmp_path):
    config = PipelineConfig(dry_run=True, output_dir=str(tmp_path))
    candidates = [
        DropCandidate(timestamp_seconds=100.0, score=0.4),
        DropCandidate(timestamp_seconds=500.0, score=0.9),
        DropCandidate(timestamp_seconds=300.0, score=0.6),
    ]

    manifest = render_clips("in.mp4", "src1", candidates, config)

    scores = [item["score"] for item in manifest]
    assert scores == sorted(scores, reverse=True)
    assert "clip_01" in str(manifest[0]["clip_path"])
    assert manifest[0]["drop_timestamp_seconds"] == 500.0


def test_build_ffmpeg_command_copy_mode():
    command = build_ffmpeg_command(
        video_path="in.mp4",
        output_path="out.mp4",
        start_seconds=15.2,
        duration_seconds=30.0,
        vertical=False,
    )

    assert command[:4] == ["ffmpeg", "-y", "-ss", "15.200"]
    assert "-c" in command
    assert "copy" in command


def test_build_ffmpeg_command_vertical_crop_mode():
    command = build_ffmpeg_command(
        video_path="in.mp4",
        output_path="out.mp4",
        start_seconds=15.2,
        duration_seconds=30.0,
        vertical=True,
        vertical_mode="crop",
    )

    assert "-vf" in command
    assert any("crop=ih*9/16:ih" in part for part in command)
    assert "libx264" in command


def test_build_ffmpeg_command_vertical_blur_mode_contains_filter():
    command = build_ffmpeg_command(
        video_path="in.mp4",
        output_path="out.mp4",
        start_seconds=15.2,
        duration_seconds=30.0,
        vertical=True,
        vertical_mode="blur",
    )

    assert "-filter_complex" in command
    assert "libx264" in command
