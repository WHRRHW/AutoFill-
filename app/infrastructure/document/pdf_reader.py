from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pdfplumber

from app.domain.errors import SourceReadError


@dataclass(frozen=True)
class PdfReadOptions:
    keep_page_markers: bool = True


class PdfReader:
    def read_text(self, file_path: str, options: PdfReadOptions | None = None) -> str:
        """
        使用 pdfplumber 按页提取文本并拼接。
        返回值要求：
        - 保留页边界分隔符（如 '\n\\n--- page N ---\\n\\n'）
        - 去除 None 页
        """
        options = options or PdfReadOptions()
        try:
            with pdfplumber.open(file_path) as pdf:
                pages: List[str] = []
                for idx, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    text = text.strip()
                    if not text:
                        continue
                    if options.keep_page_markers:
                        pages.append(f"\n\n--- page {idx} ---\n\n{text}")
                    else:
                        pages.append(text)
                return "\n".join(pages).strip()
        except Exception as e:  # noqa: BLE001
            raise SourceReadError(f"无法读取 PDF：{file_path}") from e

