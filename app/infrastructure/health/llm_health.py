from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.config.settings import Settings


@dataclass(frozen=True)
class LlmHealthResult:
    ok: bool
    message: str
    skipped: bool = False


def probe_llm(settings: Settings, timeout_sec: int = 8) -> LlmHealthResult:
    """
    TRD 迭代1/Beta：对用户透明的轻量连通性探测（不写 UI 配置项）。
    未配置密钥时跳过，不视为错误。
    """
    api_key = (settings.api_key or "").strip()
    base_url = (settings.api_base_url or "").strip()
    if not api_key or not base_url:
        return LlmHealthResult(ok=True, message="未配置模型服务，已跳过连通性检查", skipped=True)

    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:  # noqa: BLE001
        return LlmHealthResult(ok=False, message=f"缺少 openai 依赖：{e}", skipped=False)

    client = OpenAI(api_key=api_key, base_url=base_url)
    model = settings.model_name or "doubao-seed-2-0-mini-260215"
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ok"}],
            max_tokens=4,
            temperature=0,
            timeout=timeout_sec,
        )
        _ = (resp.choices[0].message.content or "").strip()
        return LlmHealthResult(ok=True, message="模型服务连通性正常", skipped=False)
    except Exception as e:  # noqa: BLE001
        return LlmHealthResult(
            ok=False,
            message=f"模型服务不可用（请检查网络或密钥）：{type(e).__name__}",
            skipped=False,
        )
