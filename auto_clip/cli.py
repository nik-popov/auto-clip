from __future__ import annotations

import argparse
from pathlib import Path

from auto_clip.config import RunRequest, load_config
from auto_clip.detect import detect_drop_candidates
from auto_clip.hotspots import fetch_youtube_heatmap
from auto_clip.ingest import ingest_source
from auto_clip.render import render_clips
from auto_clip.utils import write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto Clip: detect DJ drops and render short clips")
    parser.add_argument("source", help="YouTube URL or local media path")
    parser.add_argument("--config", dest="config_path", help="Path to JSON config file")
    parser.add_argument("--work-dir", default="artifacts", help="Directory for intermediate artifacts")
    return parser


def run_pipeline(request: RunRequest, progress=None) -> dict[str, object]:
    def report(stage: str) -> None:
        if progress is not None:
            try:
                progress(stage)
            except Exception:
                pass

    config = load_config(request.config_path)
    report("downloading")
    source_artifacts = ingest_source(request.source, request.work_dir, config)

    if config.dry_run:
        run_summary = {
            "source": request.source,
            "source_id": source_artifacts.source_id,
            "candidate_count": 0,
            "clips": [],
            "config": config.model_dump(),
            "mode": "dry-run",
        }

        report_path = Path(request.work_dir) / source_artifacts.source_id / "run_summary.json"
        write_json(report_path, run_summary)
        return run_summary

    heatmap: list[tuple[float, float, float]] = []
    if config.use_youtube_heatmap:
        heatmap = fetch_youtube_heatmap(request.source)

    report("analyzing")
    candidates = detect_drop_candidates(source_artifacts.wav_path, config, heatmap=heatmap)
    report("rendering")
    clips = render_clips(source_artifacts.video_path, source_artifacts.source_id, candidates, config)

    run_summary = {
        "source": request.source,
        "source_id": source_artifacts.source_id,
        "candidate_count": len(candidates),
        "heatmap_points": len(heatmap),
        "clips": clips,
        "config": config.model_dump(),
    }

    report_path = Path(request.work_dir) / source_artifacts.source_id / "run_summary.json"
    write_json(report_path, run_summary)
    return run_summary


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    request = RunRequest(source=args.source, config_path=args.config_path, work_dir=args.work_dir)
    summary = run_pipeline(request)
    print(f"Generated {len(summary['clips'])} clips for source {summary['source_id']}")


if __name__ == "__main__":
    main()
