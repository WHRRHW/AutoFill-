from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from app.domain.errors import RenderError, TemplateVariableMissingError
from app.domain.models import MappingReport
from app.domain.validators import align_json_to_expected_keys, build_mapping_report, keys_with_empty_values
from app.infrastructure.config import CredentialProvider
from app.infrastructure.document import SourceReader
from app.infrastructure.llm import DoubaoClient, ResponseParser
from app.infrastructure.storage import OutputNamer
from app.infrastructure.template import DocxRenderer, TemplateVariableScanner


@dataclass(frozen=True)
class ExtractOptions:
    template_name: str = "教案"


class WorkflowService:
    """
    应用层编排服务（对齐 TRD 主链路）：
    1) 扫描模板变量 expected_keys
    2) 读取源文档文本
    3) 构造 Prompt 并调用豆包模型
    4) 解析 JSON
    5) 生成 mapping_report（matched/missing/extra）
    """

    def __init__(
        self,
        source_reader: Optional[SourceReader] = None,
        variable_scanner: Optional[TemplateVariableScanner] = None,
        response_parser: Optional[ResponseParser] = None,
        renderer: Optional[DocxRenderer] = None,
        output_namer: Optional[OutputNamer] = None,
        llm_client: Optional[DoubaoClient] = None,
    ) -> None:
        self._source_reader = source_reader or SourceReader()
        self._scanner = variable_scanner or TemplateVariableScanner()
        self._parser = response_parser or ResponseParser()
        self._renderer = renderer or DocxRenderer()
        self._namer = output_namer or OutputNamer()
        self._llm = llm_client  # 若为空则在调用时创建（读取预置凭据）

    def run_extract(
        self,
        source_path: str,
        template_path: str,
        extraction_template: str = "default",
        options: Optional[ExtractOptions] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        heartbeat_callback: Optional[Callable[[int], None]] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        raw_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[Dict[str, Any], MappingReport, list[str]]:
        """
        返回：
        - json_data: dict
        - mapping_report: MappingReport
        - expected_keys: list[str]（来自模板扫描）
        """
        options = options or ExtractOptions()

        if progress_callback:
            progress_callback("扫描模板字段中…")
        expected_keys = self._scanner.scan(template_path)
        if progress_callback:
            progress_callback(f"已扫描到 {len(expected_keys)} 个模板字段。读取源文档中…")
        source_result = self._source_reader.read_text(source_path)

        if progress_callback:
            progress_callback("调用模型抽取中…（这一步可能需要几十秒）")
        llm = self._llm or DoubaoClient(CredentialProvider().load_settings())
        done = threading.Event()
        start = time.time()

        def ticker() -> None:
            # 仅更新“状态/读秒”，不写运行日志，避免 Tk after 队列堆积导致界面假死
            while not done.is_set():
                elapsed = int(time.time() - start)
                if heartbeat_callback:
                    heartbeat_callback(elapsed)
                done.wait(2.0)

        t = threading.Thread(target=ticker, daemon=True)
        t.start()
        try:
            raw = llm.extract_json(
                source_text=source_result.text,
                expected_keys=expected_keys,
                template_name=options.template_name,
                stream=stream_callback is not None,
                stream_callback=stream_callback,
            )
        finally:
            done.set()

        if raw_callback:
            raw_callback(raw)
        if progress_callback:
            progress_callback(f"模型已返回（字符数={len(raw)}），开始解析…")

        if progress_callback:
            progress_callback("解析模型返回 JSON 中…")
        raw_obj = self._parser.parse_and_validate(raw, expected_keys=expected_keys)
        matched, missing_in_json, extra_in_json = build_mapping_report(expected_keys, raw_obj)
        json_data = align_json_to_expected_keys(raw_obj, expected_keys)
        run_settings = CredentialProvider().load_settings()
        value_empty = keys_with_empty_values(json_data, expected_keys)
        if value_empty and run_settings.refill_empty_fields:
            if progress_callback:
                preview = "、".join(value_empty[:6])
                more = f" 等共 {len(value_empty)} 个" if len(value_empty) > 6 else ""
                progress_callback(f"首轮有空字段（{preview}{more}），二次补抽中…")
            try:
                refill_raw = llm.extract_json(
                    source_text=source_result.text,
                    expected_keys=value_empty,
                    template_name=f"{options.template_name}_refill",
                    stream=stream_callback is not None,
                    stream_callback=stream_callback,
                )
                if raw_callback:
                    raw_callback(f"\n\n--- refill ---\n\n{refill_raw}")
                refill_obj = self._parser.parse_and_validate(refill_raw, expected_keys=value_empty)
                refill_aligned = align_json_to_expected_keys(refill_obj, value_empty)
                for k, v in refill_aligned.items():
                    if str(v).strip() and not str(json_data.get(k, "")).strip():
                        json_data[k] = v
            except Exception as e:  # noqa: BLE001
                if progress_callback:
                    progress_callback(f"二次补抽未生效（已保留首轮结果）：{type(e).__name__}")

        value_empty = keys_with_empty_values(json_data, expected_keys)
        report = MappingReport(
            matched=matched,
            missing_in_json=missing_in_json,
            extra_in_json=extra_in_json,
            value_empty=value_empty,
        )
        if progress_callback:
            progress_callback("提取完成。")
        return json_data, report, expected_keys

    def run_render(
        self,
        template_path: str,
        final_json_data: Dict[str, Any],
        output_dir: str,
        require_all_keys: bool = False,
    ) -> str:
        """
        执行渲染并返回输出文件路径。

        require_all_keys:
        - False（默认）：允许缺失 key（模板变量对应为空则仍可生成，便于用户先出草稿）
        - True：如果模板存在变量但 JSON 缺失则阻断（更严格）
        """
        expected_keys = self._scanner.scan(template_path)
        if require_all_keys:
            _, missing, _ = build_mapping_report(expected_keys, final_json_data)
            if missing:
                raise TemplateVariableMissingError(f"模板变量缺失（未提供值）：{missing}")

        output_path = self._namer.build_output_path(template_path, output_dir)

        try:
            self._renderer.render(template_path, final_json_data, output_path)
        except RenderError:
            raise
        except Exception as e:  # noqa: BLE001
            raise RenderError("渲染失败") from e

        # 额外保护：确保输出文件确实生成
        if not Path(output_path).exists():
            raise RenderError("渲染完成但未找到输出文件")

        return output_path

