from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.infrastructure.storage import OutputNamer
from app.infrastructure.template import DocxRenderer


def main() -> None:
    template_path = str(PROJECT_ROOT / "template.docx")
    output_dir = str(PROJECT_ROOT / "outputs")

    out_path = OutputNamer().build_output_path(template_path, output_dir)

    # 如果模板里暂时没有 {{变量}}，渲染也应能生成文件（内容不变/或仅 Jinja 处理为空）
    context = {
        "k1": "v1",
        "k2": "",
    }

    DocxRenderer().render(template_path, context, out_path)
    print("render_ok=True")
    print("output_path=", out_path)


if __name__ == "__main__":
    main()

