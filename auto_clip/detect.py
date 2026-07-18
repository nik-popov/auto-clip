from __future__ import annotations

from pathlib import Path
from typing import Iterable

import librosa
import numpy as np

from auto_clip.config import PipelineConfig
from auto_clip.types import DropCandidate


def detect_drop_candidates(
    wav_path: str,
    config: PipelineConfig,
    heatmap: list[tuple[float, float, float]] | None = None,
) -> list[DropCandidate]:
    # Long sets: halve the analysis sample rate to bound memory usage.
    sr_target = config.sample_rate
    try:
        if Path(wav_path).stat().st_size > 300 * 1024 * 1024:
            sr_target = min(sr_target, 11025)
    except OSError:
        pass

    y, sr = librosa.load(wav_path, sr=sr_target, mono=True)

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

    # Blend in audience replay data (YouTube Most Replayed) when available:
    # audio finds the precise drop, the heatmap says where humans actually rewind.
    if heatmap:
        heat = heatmap_curve(frame_times, heatmap)
        weight = float(config.heatmap_weight)
        combined = combined * (1.0 - weight) + heat * weight

    # Relax the peak threshold progressively until we can fill max_clips.
    ranked: list[DropCandidate] = []
    for quantile in (0.90, 0.75, 0.60, 0.40):
        raw = _top_local_maxima(frame_times, combined, max_items=config.max_clips * 12, quantile=quantile)
        ranked = _enforce_min_spacing(
            sorted(raw, key=lambda item: item.score, reverse=True),
            spacing_seconds=float(config.min_spacing_seconds),
            max_items=config.max_clips,
        )
        if len(ranked) >= config.max_clips:
            break

    if config.adaptive_length and ranked:
        refine_clip_bounds(
            frame_times,
            combined,
            ranked,
            min_len=float(config.adaptive_min_seconds),
            max_len=float(config.adaptive_max_seconds),
        )

    return ranked


def refine_clip_bounds(
    times: np.ndarray,
    scores: np.ndarray,
    candidates: list[DropCandidate],
    min_len: float,
    max_len: float,
) -> None:
    """Set per-candidate start/end by tracing each drop's energy arc.

    Walks backward from the drop to find where the buildup begins (energy
    trough) and forward to where the drop's energy fades, bounded by
    min_len/max_len.
    """
    if len(times) < 3:
        return

    # Smooth over ~2 seconds of frames to ignore beat-level wiggle.
    frame_rate = max(1.0, len(times) / max(times[-1], 1e-6))
    window = max(3, int(frame_rate * 2.0))
    kernel = np.ones(window) / window
    envelope = np.convolve(scores, kernel, mode="same")

    max_buildup_seconds = 45.0
    for candidate in candidates:
        idx = int(np.clip(np.searchsorted(times, candidate.timestamp_seconds), 0, len(envelope) - 1))
        peak = float(envelope[idx])
        if peak <= 0:
            continue

        # Backward: buildup starts where energy dips below 25% of the peak.
        start_floor = 0.25 * peak
        start_idx = idx
        earliest = candidate.timestamp_seconds - max_buildup_seconds
        while start_idx > 0 and times[start_idx] > earliest and envelope[start_idx] > start_floor:
            start_idx -= 1
        start = float(min(times[start_idx], candidate.timestamp_seconds - 5.0))
        start = max(0.0, start)

        # Forward: clip ends where energy falls below 35% of the peak.
        end_floor = 0.35 * peak
        end_idx = idx
        latest = candidate.timestamp_seconds + max_len
        while end_idx < len(envelope) - 1 and times[end_idx] < latest and envelope[end_idx] > end_floor:
            end_idx += 1
        end = float(times[end_idx])

        # Enforce duration bounds while keeping the drop inside the clip.
        if end - start < min_len:
            end = start + min_len
        if end - start > max_len:
            overhang = (end - start) - max_len
            # Trim buildup first, then the tail.
            trim_start = min(overhang, max(0.0, candidate.timestamp_seconds - 5.0 - start))
            start += trim_start
            end = start + max_len

        candidate.start_seconds = round(start, 3)
        candidate.end_seconds = round(end, 3)


def heatmap_curve(times: np.ndarray, heatmap: list[tuple[float, float, float]]) -> np.ndarray:
    """Map replay-heatmap segments onto per-frame times, normalized to 0..1."""
    values = np.zeros_like(times)
    for start, end, value in heatmap:
        mask = (times >= start) & (times < end)
        values[mask] = np.maximum(values[mask], value)
    return _normalize(values)


def _top_local_maxima(
    times: np.ndarray, values: np.ndarray, max_items: int, quantile: float = 0.90
) -> list[DropCandidate]:
    picks: list[DropCandidate] = []
    if len(values) < 3:
        return picks

    threshold = float(np.quantile(values, quantile))
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
