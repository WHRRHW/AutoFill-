from __future__ import annotations

import os

from app.infrastructure.config.settings import Settings


class CredentialProvider:
    """
    凭据读取（对用户透明）：
    - 优先读取系统环境变量
    - 不在 UI 暴露，也不写入日志
    """

    ENV_API_KEY = "AUTO_FILL_API_KEY"
    ENV_BASE_URL = "AUTO_FILL_API_BASE_URL"
    ENV_MAX_SOURCE_CHARS = "AUTO_FILL_MAX_SOURCE_CHARS"
    ENV_MAX_OUTPUT_TOKENS = "AUTO_FILL_MAX_OUTPUT_TOKENS"
    ENV_REFILL_EMPTY = "AUTO_FILL_REFILL_EMPTY"

    def load_settings(self) -> Settings:
        api_key = (os.getenv(self.ENV_API_KEY) or "").strip()
        api_base_url = (os.getenv(self.ENV_BASE_URL) or "").strip()
        extras: dict = {}
        for key, env_name, caster in (
            ("max_source_chars", self.ENV_MAX_SOURCE_CHARS, int),
            ("max_output_tokens", self.ENV_MAX_OUTPUT_TOKENS, int),
        ):
            raw = (os.getenv(env_name) or "").strip()
            if raw:
                try:
                    extras[key] = caster(raw)
                except ValueError:
                    pass
        refill_raw = (os.getenv(self.ENV_REFILL_EMPTY) or "").strip().lower()
        if refill_raw in ("0", "false", "no", "off"):
            extras["refill_empty_fields"] = False
        return Settings(api_key=api_key, api_base_url=api_base_url, **extras)

