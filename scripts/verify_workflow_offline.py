from __future__ import annotations

from pathlib import Path
import sys
from typing import Callable, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.application import WorkflowService


class FakeDoubaoClient:
    """与 DoubaoClient.extract_json 签名保持一致，供离线脚本注入。"""

    def extract_json(
        self,
        source_text: str,
        expected_keys: list[str],
        template_name: str,
        timeout_sec: int | None = None,
        stream: bool = False,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        # 给每个 key 填一个可见值，便于验证回填是否生效
        obj = {k: f"VALUE_FOR_{k}" for k in expected_keys}
        raw = __import__("json").dumps(obj, ensure_ascii=False)
        if stream and stream_callback is not None:
            stream_callback(raw)
        return raw


def main() -> None:
    wf = WorkflowService(llm_client=FakeDoubaoClient())  # 离线验收：不需要 API Key

    source_path = str(PROJECT_ROOT / "content.docx")
    template_path = str(PROJECT_ROOT / "template.docx")

    json_data, report, expected_keys = wf.run_extract(source_path, template_path)
    print("expected_keys_count=", len(expected_keys))
    print("mapping_report=", report.model_dump())

    out_dir = str(PROJECT_ROOT / "outputs")
    out_path = wf.run_render(template_path, json_data, out_dir, require_all_keys=False)
    print("render_ok=True")
    print("output_path=", out_path)


if __name__ == "__main__":
    main()

