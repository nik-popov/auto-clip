from auto_clip.render import build_ffmpeg_command


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
