from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple


def align_json_to_expected_keys(raw_obj: Dict[str, Any], expected_keys: List[str]) -> Dict[str, Any]:
    """
    按模板字段顺序对齐：缺 key 的补 \"\"；值统一为字符串（嵌套结构序列化为 JSON 字符串）。
    仅保留 expected_keys，避免多余 key 进入渲染上下文。
    """
    out: Dict[str, Any] = {}
    for k in expected_keys:
        if k not in raw_obj:
            out[k] = ""
            continue
        v = raw_obj[k]
        if v is None:
            out[k] = ""
        elif isinstance(v, (dict, list)):
            out[k] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = str(v)
    return out


def keys_with_empty_values(aligned: Dict[str, Any], expected_keys: List[str]) -> List[str]:
    return sorted(k for k in expected_keys if str(aligned.get(k, "")).strip() == "")


def build_mapping_report(expected_keys: List[str], json_data: Dict[str, Any]) -> Tuple[List[str], List[str], List[str]]:
    """
    Compare template expected keys with json_data keys.

    Returns:
      matched, missing_in_json, extra_in_json
    """
    expected_set = set(expected_keys)
    actual_set = set(json_data.keys())

    matched = sorted(list(expected_set & actual_set))
    missing_in_json = sorted(list(expected_set - actual_set))
    extra_in_json = sorted(list(actual_set - expected_set))
    return matched, missing_in_json, extra_in_json

