from __future__ import annotations

import json

from app.domain.validators import align_json_to_expected_keys, keys_with_empty_values


def test_align_fills_missing_keys() -> None:
    raw = {"a": "1"}
    aligned = align_json_to_expected_keys(raw, ["a", "板书设计"])
    assert aligned == {"a": "1", "板书设计": ""}


def test_align_coerces_nested_to_json_str() -> None:
    raw = {"a": {"x": 1}}
    aligned = align_json_to_expected_keys(raw, ["a"])
    assert json.loads(aligned["a"]) == {"x": 1}


def test_keys_with_empty_values() -> None:
    aligned = {"a": "", "b": "  ", "c": "ok"}
    assert keys_with_empty_values(aligned, ["a", "b", "c"]) == ["a", "b"]
