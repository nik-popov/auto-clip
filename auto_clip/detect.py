from __future__ import annotations

from typing import Iterable

import librosa
import numpy as np

from auto_clip.config import PipelineConfig
from auto_clip.types import DropCandidate


def detect_drop_candidates(wav_path: str, config: PipelineConfig) -> list[DropCandidate]:
    y, sr = librosa.load(wav_path, sr=config.sample_rate, mono=True)

    hop_length = 512
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

    # Approximate spectral flux by frame-to-frame mel power change.
    melspec = librosa.feature.melspectrogram(y=y, sr=sr, hop_length=hop_length, n_mels=64)
    mel_diff = np.maximum(0.0, np.diff(melspec, axis=1))
    flux = np.concatenate([[0.0], np.mean(mel_diff, axis=0)])

    score = _normalize(onset_env) * 0.45 + _normalize(rms) * 0.25 + _normalize(flux) * 0.30

    # Favor sudden growth moments as drop candidates.
    slope = np.concatenate([[0.0], np.diff(score)])
    combined = score * 0.7 + _normalize(np.maximum(0.0, slope)) * 0.3

    frame_times = librosa.frames_to_time(np.arange(len(combined)), sr=sr, hop_length=hop_length)
    raw = _top_local_maxima(frame_times, combined, max_items=config.max_clips * 8)
    ranked = _enforce_min_spacing(
        sorted(raw, key=lambda item: item.score, reverse=True),
        spacing_seconds=float(config.min_spacing_seconds),
        max_items=config.max_clips,
    )
    return ranked


def _top_local_maxima(times: np.ndarray, values: np.ndarray, max_items: int) -> list[DropCandidate]:
    picks: list[DropCandidate] = []
    if len(values) < 3:
        return picks

    threshold = float(np.quantile(values, 0.90))
    for idx in range(1, len(values) - 1):
        if values[idx] < threshold:
            continue
        if values[idx] >= values[idx - 1] and values[idx] > values[idx + 1]:
            picks.append(DropCandidate(timestamp_seconds=float(times[idx]), score=float(values[idx])))

    picks.sort(key=lambda item: item.score, reverse=True)
    return picks[:max_items]


def _enforce_min_spacing(
    candidates: Iterable[DropCandidate], spacing_seconds: float, max_items: int
) -> list[DropCandidate]:
    selected: list[DropCandidate] = []
    for candidate in candidates:
        if all(abs(candidate.timestamp_seconds - kept.timestamp_seconds) >= spacing_seconds for kept in selected):
            selected.append(candidate)
        if len(selected) >= max_items:
            break

    selected.sort(key=lambda item: item.timestamp_seconds)
    return selected


def _normalize(values: np.ndarray) -> np.ndarray:
    if len(values) == 0:
        return values
    low = float(np.min(values))
    high = float(np.max(values))
    if high <= low:
        return np.zeros_like(values)
    return (values - low) / (high - low)
