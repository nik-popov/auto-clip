from __future__ import annotations

import json
import subprocess


def fetch_youtube_heatmap(source: str) -> list[tuple[float, float, float]]:
    """Fetch YouTube 'Most Replayed' heatmap segments as (start, end, value).

    Returns an empty list for non-YouTube sources, videos without heatmap
    data, or on any extraction failure.
    """
    if "youtube.com" not in source and "youtu.be" not in source:
        return []

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--skip-download",
                "--no-warnings",
                "--dump-single-json",
                source,
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (subprocess.SubprocessError, OSError):
        return []

    if result.returncode != 0:
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    segments = data.get("heatmap") or []
    heatmap: list[tuple[float, float, float]] = []
    for segment in segments:
        try:
            heatmap.append(
                (
                    float(segment["start_time"]),
                    float(segment["end_time"]),
                    float(segment["value"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue

    return heatmap
