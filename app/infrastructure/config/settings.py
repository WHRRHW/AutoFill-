from __future__ import annotations

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """
    运行配置（用户透明）：
    - 仅支持开发/运维预置：环境变量或本地加密配置（本迭代先实现环境变量读取）
    - UI 不提供任何配置入口
    """

    api_base_url: str = Field(default="")
    api_key: str = Field(default="")
    model_name: str = Field(default="doubao-seed-2-0-mini-260215")
    request_timeout_sec: int = Field(default=45, ge=5, le=180)
    max_retries: int = Field(default=2, ge=0, le=5)
    """送入模型的源文本最大字符数（超出截断首尾易丢小节，如文档后部「板书」）。"""
    max_source_chars: int = Field(default=120_000, ge=10_000, le=500_000)
    """生成 JSON 的上限 token；过小会导致长模板字段在输出末尾被截断、解析缺 key。"""
    max_output_tokens: int = Field(default=16_384, ge=512, le=128_000)
    """首轮抽取后是否对仍为空的字段发起第二次补抽（多一次请求）。"""
    refill_empty_fields: bool = Field(default=True)

    model_config = {
        "protected_namespaces": (),
    }

