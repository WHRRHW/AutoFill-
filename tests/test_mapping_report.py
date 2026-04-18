from __future__ import annotations

from app.domain.validators import build_mapping_report


def test_build_mapping_report_basic() -> None:
    m, miss, extra = build_mapping_report(
        ["a", "b", "c"],
        {"b": 1, "d": 2},
    )
    assert m == ["b"]
    assert miss == ["a", "c"]
    assert extra == ["d"]
