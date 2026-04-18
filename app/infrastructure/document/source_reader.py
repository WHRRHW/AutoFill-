from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.domain.enums import FileType
from app.domain.errors import InvalidFileTypeError, SourceReadError

from .docx_reader import DocxReader, DocxReadOptions
from .pdf_reader import PdfReader, PdfReadOptions


@dataclass(frozen=True)
class SourceReadResult:
    file_type: FileType
    text: str


class SourceReader:
    def __init__(self) -> None:
        self._docx = DocxReader()
        self._pdf = PdfReader()

    def read_text(self, file_path: str) -> SourceReadResult:
        """根据扩展名分发到 PDF/DOCX Reader，返回统一纯文本。"""
        p = Path(file_path)
        if not p.exists():
            raise SourceReadError(f"文件不存在：{file_path}")

        suffix = p.suffix.lower().lstrip(".")
        if suffix == FileType.docx.value:
            text = self._docx.read_text(str(p), DocxReadOptions())
            return SourceReadResult(file_type=FileType.docx, text=text)
        if suffix == FileType.pdf.value:
            text = self._pdf.read_text(str(p), PdfReadOptions())
            return SourceReadResult(file_type=FileType.pdf, text=text)

        raise InvalidFileTypeError(f"不支持的文件类型：{p.suffix}")

