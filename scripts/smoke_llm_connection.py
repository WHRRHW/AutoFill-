from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.infrastructure.config import CredentialProvider  # type: ignore
from app.infrastructure.llm import DoubaoClient, ResponseParser  # type: ignore


def main() -> None:
    s = CredentialProvider().load_settings()
    c = DoubaoClient(s)
    parser = ResponseParser()

    # 不依赖模板扫描，保证至少能触发一次请求
    expected_keys = ["课题", "教学目标"]
    source_text = "源文档示例：课题是《液体的压强》。教学目标包括理解液体压强与相关计算。"
    raw = c.extract_json(
        source_text=source_text,
        expected_keys=expected_keys,
        template_name="smoke",
        timeout_sec=20,
        stream=False,
    )
    print("raw_prefix=", raw[:200])
    obj = parser.parse_and_validate(raw, expected_keys=expected_keys)
    print("parsed_keys=", list(obj.keys()))


if __name__ == "__main__":
    main()

