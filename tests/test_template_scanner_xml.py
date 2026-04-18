from __future__ import annotations

from app.infrastructure.template.template_variable_scanner import (
    PLACEHOLDER_PATTERN,
    _joined_text_from_docx_xml,
    _normalize_placeholder_braces,
)


def test_joined_text_recovers_split_placeholder() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r><w:t>前缀{{板书</w:t></w:r>
      <w:r><w:t>设计}}后缀</w:t></w:r>
    </w:p>
  </w:body>
</w:document>""".encode("utf-8")
    merged = _joined_text_from_docx_xml(xml)
    assert "前缀{{板书设计}}后缀" == merged
    assert PLACEHOLDER_PATTERN.findall(merged) == ["板书设计"]


def test_normalize_fullwidth_braces() -> None:
    s = _normalize_placeholder_braces("｛｛板书设计｝｝")
    assert PLACEHOLDER_PATTERN.findall(s) == ["板书设计"]
