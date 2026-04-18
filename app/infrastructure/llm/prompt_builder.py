from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PromptBuildOptions:
    template_name: str = "default"
    max_source_chars: int = 120_000


class PromptBuilder:
    def build(
        self,
        source_text: str,
        expected_keys: List[str],
        template_name: str,
        options: PromptBuildOptions | None = None,
    ) -> str:
        """
        强约束 Prompt（动态 key）：
        - 只输出一个 JSON 对象（禁止解释、禁止 Markdown）
        - JSON key 必须与 expected_keys 完全一致（逐字匹配）
        - 找不到答案的字段输出空字符串 ""，不得省略该 key
        - 禁止输出额外 key
        """
        options = options or PromptBuildOptions(template_name=template_name)
        src = source_text or ""
        if len(src) > options.max_source_chars:
            src = src[: options.max_source_chars]

        keys_json = json.dumps(expected_keys, ensure_ascii=False)

        n = len(expected_keys)
        board_rule = ""
        if any("板书" in k for k in expected_keys):
            board_rule = (
                "7) 字段列表含板书类名称时，须通读全文检索“板书”“主板书”“板书内容”或小节标题相近段落，"
                "将板书相关表述写入对应字段；禁止仅因该段在文档后部而留空。\n"
            )
        return (
            "你是一个信息抽取助手。你将从【源文档内容】中抽取信息，并只输出一个 JSON 对象。\n"
            "严格遵守以下规则：\n"
            f"1) 仅输出 JSON（不要输出任何解释、不要输出 Markdown、不要输出代码块）。\n"
            f"2) JSON 的 key 必须与【字段列表】完全一致：逐字匹配、一个不能少、一个不能多；"
            f"输出对象必须恰好包含 {n} 个 key（与列表长度一致）。\n"
            "3) 禁止省略 key：即使某个字段在文档里不好找，也必须输出该 key；"
            "可以先根据文中小节标题、就近段落、表格中的文字去推断归属。\n"
            "4) 仅在【源文档内容】中确实没有任何相关表述时，该字段 value 才可为空字符串 \"\"；"
            "若文档中有同义或相近表述（如“板书”“板书设计”“主板书”“板书内容”等应对应“板书设计”类字段；"
            "“课程思政”“思政”“育人”等应对应“思政元素”类字段），必须写入该字段，禁止无故留空。\n"
            "5) value 统一为字符串；可从原文摘编整合，但要用连贯书面语，不要只输出标题而无实质内容（除非原文仅有标题）。\n"
            "6) 文风：自然通顺的整段中文；不要用“首先/其次/综上所述”等套话，不要分点列举（不要用 1.2.3. 或 “- ” 条目），"
            "不要写成 AI 腔总结模板；如源文档本身是条目，请改写为连贯句子。\n"
            f"{board_rule}"
            f"\n【字段列表】\n{keys_json}\n"
            f"\n【模板名称】\n{template_name}\n"
            f"\n【源文档内容】\n{src}\n"
        )

