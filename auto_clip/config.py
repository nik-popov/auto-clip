from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class PipelineConfig(BaseModel):
    clip_duration_seconds: int = Field(default=30, ge=10, le=120)
    pre_drop_seconds: int = Field(default=10, ge=0, le=90)
    max_clips: int = Field(default=12, ge=1, le=100)
    min_spacing_seconds: int = Field(default=45, ge=10, le=600)
    sample_rate: int = Field(default=22050, ge=8000, le=96000)
    render_vertical_9x16: bool = False
    use_youtube_heatmap: bool = True
    heatmap_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    dry_run: bool = False
    output_dir: str = "outputs"


class RunRequest(BaseModel):
    source: str
    config_path: str | None = None
    work_dir: str = "artifacts"


def load_config(config_path: str | None) -> PipelineConfig:
    if not config_path:
        return PipelineConfig()

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    return PipelineConfig.model_validate(data)
