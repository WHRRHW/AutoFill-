from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from app.domain.errors import RenderError


@dataclass(frozen=True)
class RenderOptions:
    forbid_overwrite_template: bool = True
    create_parent_dirs: bool = True


class DocxRenderer:
    def render(self, template_path: str, context: Dict[str, Any], output_path: str, options: RenderOptions | None = None) -> None:
        """
        使用 docxtpl.DocxTemplate 渲染并另存为新文件。
        无损红线：
        - 仅允许 docxtpl 渲染占位符
        - 禁止对模板执行任何结构性写操作（表格/样式/段落）
        """
        options = options or RenderOptions()

        tpl = Path(template_path)
        out = Path(output_path)

        try:
            if options.forbid_overwrite_template:
                if tpl.resolve() == out.resolve():
                    raise RenderError("输出路径不能与模板路径相同（禁止覆盖模板）")

            if options.create_parent_dirs:
                out.parent.mkdir(parents=True, exist_ok=True)

            # 延迟导入，避免未安装 docxtpl 时影响其它模块验收
            from docxtpl import DocxTemplate  # type: ignore

            doc = DocxTemplate(str(tpl))
            doc.render(context or {})
            doc.save(str(out))
        except RenderError:
            raise
        except Exception as e:  # noqa: BLE001
            raise RenderError(f"渲染失败：{e}") from e

