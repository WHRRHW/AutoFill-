from __future__ import annotations

import json
import re
from typing import Any, Dict, List

try:
    import orjson  # type: ignore
except Exception:  # noqa: BLE001
    orjson = None  # type: ignore

from app.domain.errors import NonJsonResponseError, SchemaValidationError


_JSON_BLOCK_RE = re.compile(r"```json\s*(\{[\s\S]*?\})\s*```", re.IGNORECASE)


class ResponseParser:
    def parse_and_validate(self, model_output: str, expected_keys: List[str]) -> Dict[str, Any]:
        """
        1) 尝试直接 JSON 解析
        2) 若失败，提取 ```json ...``` 中的对象再解析
        3) 仍失败则抛出 NonJsonResponseError
        4) 校验：必须为 JSON object；key 必须为字符串

        注意：本层不强行修正 key 的缺失/多余；由上层生成 mapping_report 并提示用户修正。
        """
        raw = (model_output or "").strip()
        if not raw:
            raise NonJsonResponseError("模型输出为空，无法解析为 JSON")

        obj = self._loads_json_object(raw)
        if obj is None:
            m = _JSON_BLOCK_RE.search(raw)
            if m:
                obj = self._loads_json_object(m.group(1).strip())
        if obj is None:
            candidate = self._extract_first_json_object(raw)
            if candidate:
                obj = self._loads_json_object(candidate)

        if obj is None:
            raise NonJsonResponseError("模型输出不是有效 JSON object")

        if not isinstance(obj, dict):
            raise SchemaValidationError("模型输出不是 JSON object")

        for k in obj.keys():
            if not isinstance(k, str):
                raise SchemaValidationError("JSON key 必须为字符串")

        # expected_keys 参数用于上层比对；这里仅做轻量校验，避免误伤可恢复结果
        if not isinstance(expected_keys, list):
            raise SchemaValidationError("expected_keys 类型错误")

        return obj

    def _loads_json_object(self, text: str) -> Dict[str, Any] | None:
        try:
            if orjson is not None:
                return orjson.loads(text)  # type: ignore[no-any-return]
            return json.loads(text)  # type: ignore[no-any-return]
        except Exception:  # noqa: BLE001
            return None

    def _extract_first_json_object(self, text: str) -> str | None:
        """
        从混合文本中提取第一个“平衡大括号”的 JSON 对象字符串。
        支持跳过字符串内部的大括号和转义字符。
        """
        start = text.find("{")
        if start < 0:
            return None

        depth = 0
        in_str = False
        escaped = False

        for i in range(start, len(text)):
            ch = text[i]

            if in_str:
                if escaped:
                    escaped = False
                    continue
                if ch == "\\":
                    escaped = True
                    continue
                if ch == '"':
                    in_str = False
                continue

            if ch == '"':
                in_str = True
                continue
            if ch == "{":
                depth += 1
                continue
            if ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

        return None

