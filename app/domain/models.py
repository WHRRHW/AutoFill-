from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from .enums import FileType


class SourceDocument(BaseModel):
    path: str
    file_type: FileType
    size_bytes: int


class TemplateDocument(BaseModel):
    path: str
    variables: List[str] = Field(default_factory=list)


class TemplateExtractionSchema(BaseModel):
    """
    动态抽取 schema：由模板中的 {{变量名}} 扫描得到，用于驱动 LLM 输出 JSON 的 key 集合。
    Demo/Beta 阶段不强制值类型（统一以字符串语义输出/渲染），避免引入超出 PRD 范围的复杂规则。
    """

    expected_keys: List[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    raw_text: str
    json_data: Dict[str, Any]
    model_name: str
    warnings: List[str] = Field(default_factory=list)

    model_config = {
        "protected_namespaces": (),
    }


class MappingReport(BaseModel):
    matched: List[str] = Field(default_factory=list)
    missing_in_json: List[str] = Field(default_factory=list)
    extra_in_json: List[str] = Field(default_factory=list)
    value_empty: List[str] = Field(
        default_factory=list,
        description="value 为空串的字段（含模型漏 key 已补空的），便于核对模板留白。",
    )


class RenderRequest(BaseModel):
    template_path: str
    output_path: str
    context: Dict[str, Any]

