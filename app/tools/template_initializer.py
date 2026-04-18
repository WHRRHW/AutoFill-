from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from docx import Document


@dataclass(frozen=True)
class InitOptions:
    """
    模板初始化配置（兼容一般教案表格）：
    - 识别“备注”列并避免往备注列填占位符
    - 自动选择“字段列”（变化最多的左侧列）与“内容列”（字段列右侧第一个空单元格）
    - 仅在目标单元格为空时插入 {{字段名}}，避免覆盖人工内容
    """

    prefer_left_most_label_col: bool = True
    skip_labels: Tuple[str, ...] = ("备注",)


class TemplateInitializer:
    def init_from_table_headings(self, template_path: str, output_path: str, options: InitOptions | None = None) -> List[str]:
        """
        基于表格栏标题自动生成占位符，并写入模板副本。

        返回：所有生成的占位符变量名列表（不带 {{}}）。
        """
        options = options or InitOptions()
        src = Path(template_path)
        dst = Path(output_path)

        doc = Document(str(src))

        created_vars: List[str] = []

        for table in doc.tables:
            label_col, remarks_col = self._infer_columns(table, options)
            for row in table.rows:
                if not row.cells:
                    continue

                if label_col is None or label_col >= len(row.cells):
                    continue

                raw_label = (row.cells[label_col].text or "").strip()
                if not raw_label:
                    continue

                # 简单清洗：去掉常见的结尾标点
                label = raw_label.rstrip("：:，, ")
                if not label:
                    continue

                if label in options.skip_labels:
                    continue

                target_cell = self._choose_target_cell(row.cells, label_col, remarks_col)
                if target_cell is None:
                    continue

                if (target_cell.text or "").strip():
                    continue  # 已有内容则跳过，避免覆盖人工内容

                placeholder = f"{{{{{label}}}}}"
                target_cell.text = placeholder
                created_vars.append(label)

        dst.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(dst))
        return created_vars

    def _infer_columns(self, table, options: InitOptions) -> Tuple[Optional[int], Optional[int]]:
        """
        推断：
        - remarks_col: 包含“备注”的列（优先从第一行/表头行推断）
        - label_col: 字段列（左侧变化最多、且非备注列）
        """
        # 推断备注列：任一行出现“备注”且该列较稳定
        remarks_candidates = {}
        for r in table.rows[:3]:
            for idx, cell in enumerate(r.cells):
                txt = (cell.text or "").strip()
                if txt == "备注":
                    remarks_candidates[idx] = remarks_candidates.get(idx, 0) + 1
        remarks_col = max(remarks_candidates, key=remarks_candidates.get) if remarks_candidates else None

        # 推断字段列：统计每列的“非空数量”和“唯一值数量”
        col_stats = []
        max_cols = max((len(r.cells) for r in table.rows), default=0)
        for c in range(max_cols):
            if remarks_col is not None and c == remarks_col:
                continue
            values: List[str] = []
            non_empty = 0
            for r in table.rows:
                if c >= len(r.cells):
                    continue
                t = (r.cells[c].text or "").strip()
                if not t:
                    continue
                non_empty += 1
                values.append(t.rstrip("：:，, "))
            uniq = len(set(values))
            # 排除“几乎不变的大标题列”（uniq 很小）
            score = uniq * 10 + non_empty
            col_stats.append((score, uniq, non_empty, c))

        if not col_stats:
            return None, remarks_col

        # 选择 score 最大的列作为字段列；若 prefer_left_most_label_col，则同分取更左
        col_stats.sort(key=lambda x: (-x[0], x[3] if options.prefer_left_most_label_col else 0))
        label_col = col_stats[0][3]
        return label_col, remarks_col

    def _choose_target_cell(self, cells, label_col: int, remarks_col: Optional[int]):
        # 内容列候选范围：字段列右侧到备注列左侧（若存在备注列）
        end = (remarks_col - 1) if remarks_col is not None else (len(cells) - 1)
        if end <= label_col:
            end = len(cells) - 1

        # 选择字段列右侧第一个“空白”单元格
        for idx in range(label_col + 1, end + 1):
            t = (cells[idx].text or "").strip()
            if not t:
                return cells[idx]
        return None

