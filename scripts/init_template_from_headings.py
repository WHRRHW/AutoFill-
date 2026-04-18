from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.tools import TemplateInitializer


def main() -> None:
    src = PROJECT_ROOT / "template.docx"
    dst_dir = PROJECT_ROOT / "templates_initialized"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{src.stem}_with_placeholders_v2{src.suffix}"

    print(f"原始模板：{src}")
    print(f"副本输出：{dst}")

    created = TemplateInitializer().init_from_table_headings(str(src), str(dst))

    print("生成占位符变量数：", len(created))
    if created:
        print("示例变量：", created[:20])
    else:
        print("未检测到可用的表头（请确认第一列是否为字段标题，如“课题/学情分析/教学目标”等）。")


if __name__ == "__main__":
    main()

