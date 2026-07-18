from __future__ import annotations

from pydantic import BaseModel, Field


class DropCandidate(BaseModel):
    timestamp_seconds: float = Field(ge=0)
    score: float = Field(ge=0)


class SourceArtifacts(BaseModel):
    source_id: str
    video_path: str
    wav_path: str
