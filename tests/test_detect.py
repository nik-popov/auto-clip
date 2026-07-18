from auto_clip.detect import _enforce_min_spacing
from auto_clip.types import DropCandidate


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
