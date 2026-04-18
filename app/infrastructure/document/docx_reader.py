from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Union

from docx.document import Document as _Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx import Document

from app.domain.errors import SourceReadError


@dataclass(frozen=True)
class DocxReadOptions:
    cell_delimiter: str = "\t"
    row_delimiter: str = "\n"
    block_delimiter: str = "\n"
    keep_empty_paragraphs: bool = False


def _iter_block_items(parent: _Document) -> Iterable[Union[Paragraph, Table]]:
    """
    Yield paragraphs and tables in the order they appear in the document body.
    """
    body = parent.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


class DocxReader:
    def read_text(self, file_path: str, options: DocxReadOptions | None = None) -> str:
        """
        使用 python-docx 提取段落 + 表格文本。

        约束（来自 TRD）：
        - 按阅读顺序拼接
        - 单元格内容以制表符分隔
        - 输出统一纯文本供后续模型处理
        """
        options = options or DocxReadOptions()
        try:
            doc = Document(file_path)
        except Exception as e:  # noqa: BLE001
            raise SourceReadError(f"无法读取 DOCX：{file_path}") from e

        blocks: List[str] = []
        for block in _iter_block_items(doc):
            if isinstance(block, Paragraph):
                text = (block.text or "").strip()
                if text or options.keep_empty_paragraphs:
                    blocks.append(text)
            elif isinstance(block, Table):
                table_lines: List[str] = []
                for row in block.rows:
                    row_cells = [(cell.text or "").strip() for cell in row.cells]
                    table_lines.append(options.cell_delimiter.join(row_cells))
                if table_lines:
                    blocks.append(options.row_delimiter.join(table_lines))

        return options.block_delimiter.join(blocks).strip()

