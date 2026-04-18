from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from app.domain.errors import LlmRequestError
from app.infrastructure.config.settings import Settings
from app.infrastructure.llm.prompt_builder import PromptBuilder


@dataclass(frozen=True)
class LlmCallOptions:
    timeout_sec: int = 45


class DoubaoClient:
    """
    豆包模型调用（API 对用户透明）：
    - model 固定：doubao-seed-2-0-mini-260215（可被 Settings 覆盖但不暴露给 UI）
    - base_url / api_key 由 Settings 提供（开发/运维预置）
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._prompt_builder = PromptBuilder()

    @property
    def model_name(self) -> str:
        return self._settings.model_name or "doubao-seed-2-0-mini-260215"

    def extract_json(
        self,
        source_text: str,
        expected_keys: List[str],
        template_name: str,
        timeout_sec: int | None = None,
        stream: bool = False,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        调用 openai SDK 访问豆包，返回模型原始文本（期望 JSON 字符串）。
        内置重试：网络错误/超时/限流时最多 Settings.max_retries 次（默认 2）。
        """
        timeout = timeout_sec or self._settings.request_timeout_sec
        from app.infrastructure.llm.prompt_builder import PromptBuildOptions

        p_opts = PromptBuildOptions(
            template_name=template_name,
            max_source_chars=self._settings.max_source_chars,
        )
        prompt = self._prompt_builder.build(source_text, expected_keys, template_name, options=p_opts)
        return self._call_with_retry(prompt, timeout_sec=timeout, stream=stream, stream_callback=stream_callback)

    def _call_with_retry(
        self,
        prompt: str,
        timeout_sec: int,
        stream: bool = False,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        return self._call(prompt, timeout_sec=timeout_sec, stream=stream, stream_callback=stream_callback)

    def _call(
        self,
        prompt: str,
        timeout_sec: int,
        stream: bool = False,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        api_key = (self._settings.api_key or "").strip()
        base_url = (self._settings.api_base_url or "").strip()

        if not api_key or not base_url:
            raise LlmRequestError(
                "模型服务未配置（缺少 AUTO_FILL_API_KEY 或 AUTO_FILL_API_BASE_URL 环境变量）"
            )

        # 延迟导入，避免未安装 openai 时影响其它模块验收
        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:  # noqa: BLE001
            raise LlmRequestError("缺少 openai 依赖，请安装 requirements.txt") from e

        client = OpenAI(api_key=api_key, base_url=base_url)

        last_err: Exception | None = None
        attempts = max(1, int(self._settings.max_retries) + 1)  # max_retries=2 => 总尝试 3 次

        for _ in range(attempts):
            try:
                if stream and stream_callback is not None:
                    full = ""
                    resp = client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "你是一个只输出 JSON 的抽取引擎。必须输出完整、可解析的一个 JSON 对象，"
                                    "包含用户要求的全部 key，不要中途截断；无依据时对应 value 用空字符串。"
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0,
                        timeout=timeout_sec,
                        max_tokens=self._settings.max_output_tokens,
                        stream=True,
                    )
                    for evt in resp:
                        # 兼容不同 SDK/服务的 delta 字段命名
                        delta_text: str | None = None
                        try:
                            choice0 = evt.choices[0]  # type: ignore[attr-defined]
                            delta = getattr(choice0, "delta", None)
                            if delta is None:
                                continue
                            # delta 可能是对象，也可能是 dict
                            delta_text = getattr(delta, "content", None) or getattr(delta, "text", None)
                            if delta_text:
                                delta_text = str(delta_text)
                            else:
                                if isinstance(delta, dict):
                                    delta_text = delta.get("content") or delta.get("text")
                                    if delta_text:
                                        delta_text = str(delta_text)
                        except Exception:
                            delta_text = None

                        if not delta_text:
                            continue

                        full += delta_text
                        stream_callback(delta_text)
                    return full.strip()

                resp = client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "你是一个只输出 JSON 的抽取引擎。必须输出完整、可解析的一个 JSON 对象，"
                                "包含用户要求的全部 key，不要中途截断；无依据时对应 value 用空字符串。"
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0,
                    timeout=timeout_sec,
                    max_tokens=self._settings.max_output_tokens,
                )
                content = (resp.choices[0].message.content or "").strip()
                return content
            except Exception as e:  # noqa: BLE001
                last_err = e

        raise LlmRequestError("模型请求失败（已重试）") from last_err

