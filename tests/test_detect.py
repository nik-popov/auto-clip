import numpy as np

from auto_clip.detect import _enforce_min_spacing, heatmap_curve, refine_clip_bounds
from auto_clip.types import DropCandidate


def test_refine_clip_bounds_traces_energy_arc():
    # 300s timeline at 1 frame/sec: quiet -> buildup -> drop plateau -> fade.
    times = np.arange(300, dtype=float)
    scores = np.zeros(300)
    scores[100:120] = np.linspace(0.1, 1.0, 20)  # buildup 100-120
    scores[120:160] = 1.0                        # drop plateau 120-160
    scores[160:180] = np.linspace(1.0, 0.05, 20) # fade

    candidate = DropCandidate(timestamp_seconds=125.0, score=1.0)
    refine_clip_bounds(times, scores, [candidate], min_len=20.0, max_len=90.0)

    assert candidate.start_seconds is not None and candidate.end_seconds is not None
    # Starts during/before the buildup, before the drop.
    assert candidate.start_seconds < 120.0
    # Ends after the plateau, during/after the fade.
    assert candidate.end_seconds > 155.0
    duration = candidate.end_seconds - candidate.start_seconds
    assert 20.0 <= duration <= 90.0


def test_refine_clip_bounds_enforces_max_length():
    times = np.arange(600, dtype=float)
    scores = np.ones(600)  # constant energy: no natural boundaries

    candidate = DropCandidate(timestamp_seconds=300.0, score=1.0)
    refine_clip_bounds(times, scores, [candidate], min_len=20.0, max_len=60.0)

    duration = candidate.end_seconds - candidate.start_seconds
    assert duration <= 60.0 + 1e-6


def test_enforce_min_spacing_prefers_higher_scores():
    candidates = [
        DropCandidate(timestamp_seconds=100.0, score=0.9),
        DropCandidate(timestamp_seconds=110.0, score=0.8),
        DropCandidate(timestamp_seconds=170.0, score=0.85),
    ]

    selected = _enforce_min_spacing(candidates, spacing_seconds=45.0, max_items=5)

    assert [round(item.timestamp_seconds) for item in selected] == [100, 170]


def test_enforce_min_spacing_limits_count():
    candidates = [
        DropCandidate(timestamp_seconds=20.0, score=0.9),
        DropCandidate(timestamp_seconds=70.0, score=0.8),
        DropCandidate(timestamp_seconds=130.0, score=0.7),
    ]

    selected = _enforce_min_spacing(candidates, spacing_seconds=30.0, max_items=2)

    assert len(selected) == 2


def test_heatmap_curve_maps_segments_to_times():
    times = np.array([0.0, 5.0, 15.0, 25.0, 35.0])
    heatmap = [(0.0, 10.0, 0.2), (10.0, 20.0, 1.0), (20.0, 30.0, 0.5)]

    curve = heatmap_curve(times, heatmap)

    # Peak replay segment (10-20s) should normalize to max.
    assert curve[2] == 1.0
    # Outside all segments (35s) should be zero.
    assert curve[4] == 0.0
    # Lower segments scale proportionally after normalization.
    assert 0.0 < curve[0] < curve[3] < curve[2]


def test_heatmap_curve_empty_returns_zeros():
    times = np.array([0.0, 10.0])

    curve = heatmap_curve(times, [])

    assert curve.tolist() == [0.0, 0.0]
