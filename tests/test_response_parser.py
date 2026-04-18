from __future__ import annotations

import pytest

from app.domain.errors import NonJsonResponseError, SchemaValidationError
from app.infrastructure.llm.response_parser import ResponseParser


def test_parse_direct_json() -> None:
    p = ResponseParser()
    obj = p.parse_and_validate('{"a": "1", "b": 2}', ["a", "b"])
    assert obj == {"a": "1", "b": 2}


def test_parse_fenced_json_block() -> None:
    p = ResponseParser()
    raw = '说明\n```json\n{"x": "y"}\n```\n'
    obj = p.parse_and_validate(raw, ["x"])
    assert obj == {"x": "y"}


def test_parse_mixed_text_balanced_brace() -> None:
    p = ResponseParser()
    raw = '前缀文字 {"k": "v", "n": 1} 后缀'
    obj = p.parse_and_validate(raw, ["k", "n"])
    assert obj == {"k": "v", "n": 1}


def test_braces_inside_string() -> None:
    p = ResponseParser()
    raw = r'{"msg": "hello {not json}"}'
    obj = p.parse_and_validate(raw, ["msg"])
    assert obj["msg"] == "hello {not json}"


def test_empty_raises() -> None:
    p = ResponseParser()
    with pytest.raises(NonJsonResponseError):
        p.parse_and_validate("", ["a"])


def test_not_object_raises() -> None:
    p = ResponseParser()
    with pytest.raises(SchemaValidationError):
        p.parse_and_validate("[1,2]", [])
