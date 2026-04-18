from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox

from app.application import WorkflowService
from app.domain.errors import AutoFillError
from app.infrastructure.config import CredentialProvider, UserSettingsStore
from app.infrastructure.health import probe_llm
from app.infrastructure.logging import get_logger
from app.infrastructure.storage import TemplateLibrary, TemplateItem
from app.infrastructure.template import TemplateVariableScanner


class AppWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("智能文档结构化填报助手")
        self.geometry("960x720")
        self.minsize(880, 640)

        # 深色界面更易读顶部「白色操作说明」；用户仍可在系统里用浅色时看下方主区域
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._wf = WorkflowService()
        self._json_data: Dict[str, Any] = {}
        self._mapping: Optional[Dict[str, List[str]]] = None
        self._expected_keys: List[str] = []
        self._logger = get_logger("autofill.ui")
        self._user_settings = UserSettingsStore()
        self._template_library = TemplateLibrary(store=self._user_settings)
        self._template_items: List[TemplateItem] = []
        self._selected_template_id: Optional[str] = None
        self._scanner = TemplateVariableScanner()
        # 流式输出节流：避免 after 队列堆积导致界面“卡住”
        self._stream_buffer: List[str] = []
        self._stream_flush_scheduled: bool = False

        self._build_widgets()
        self._refresh_template_library_path_label()
        self._refresh_output_path_label()
        self._refresh_template_library()
        threading.Thread(target=self._startup_health_check, daemon=True).start()

    # UI 构建
    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        # 上半：可滚动（鼠标滚轮上下浏览）；下半：日志/结果固定，避免一起滚走
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        top.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 4))
        top.columnconfigure(1, weight=1)
        self._bind_scroll_mousewheel(top)

        # —— 顶部：操作顺序（白色字，便于不熟悉电脑的用户跟着做）——
        guide = ctk.CTkFrame(top, fg_color=("#1e3a5f", "#1e3a5f"), corner_radius=10)
        guide.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        guide.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            guide,
            text="请按下面顺序操作（第一次使用建议完整看一遍）",
            text_color="white",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))
        _steps = (
            "① 选源文档：点右侧「选择文件」，选要从中读取内容的 Word 或 PDF（您的教案材料等）。\n"
            "② 选模板：点「选择文件」，选已经放好 {{变量名}} 的 Word 模板（例如 {{课题}}，需事先在 Word 里编辑好）。\n"
            "③（建议做一次）加入模板库：选好模板后点「加入模板库」，以后从「模板库」下拉框一键选用，不用每次找文件夹。\n"
            "④（可选）目录设置：点「设置库目录」把模板存到 D/E 盘；点「设置输出目录」决定生成的 Word 保存位置。\n"
            "⑤ 提取：点下方蓝色「1. 开始提取」，请耐心等待；左侧看进度，右侧会出现结果，可小幅修改文字。\n"
            "⑥ 生成：点「2. 生成文档」，完成后点「打开输出目录」或到上一步设置的文件夹里打开新的 Word。"
        )
        ctk.CTkLabel(
            guide,
            text=_steps,
            text_color="white",
            font=ctk.CTkFont(size=13),
            anchor="w",
            justify="left",
            wraplength=900,
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))

        # 源文档
        ctk.CTkLabel(top, text="【第1步】源文档（材料）", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(4, 0)
        )
        ctk.CTkLabel(top, text="源文档 A：").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_source = ctk.CTkEntry(top, placeholder_text="点右侧按钮选择 Word 或 PDF…")
        self.entry_source.grid(row=2, column=1, sticky="ew", padx=5)
        ctk.CTkButton(top, text="选择文件", command=self._choose_source, width=100).grid(row=2, column=2, padx=5)

        # 模板文档
        ctk.CTkLabel(top, text="【第2步】模板（要填进去的 Word）", font=ctk.CTkFont(weight="bold")).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(10, 0)
        )
        ctk.CTkLabel(top, text="模板 B：").grid(row=4, column=0, sticky="w", pady=5)
        self.entry_template = ctk.CTkEntry(top, placeholder_text="选已含 {{变量}} 的 Word 模板…")
        self.entry_template.grid(row=4, column=1, sticky="ew", padx=5)
        ctk.CTkButton(top, text="选择文件", command=self._choose_template, width=100).grid(row=4, column=2, padx=5)
        self.lbl_template_hint = ctk.CTkLabel(
            top,
            text="说明：模板里要有像 {{课题}} 这样的占位符，程序才能把内容填到对应位置；不会做模板可请同事帮忙做一次。",
            text_color="gray60",
            wraplength=880,
            anchor="w",
            justify="left",
        )
        self.lbl_template_hint.grid(row=5, column=0, columnspan=3, sticky="ew", padx=(0, 5), pady=(0, 6))

        # 模板库
        ctk.CTkLabel(top, text="【第3步·可选】模板库（常用模板一键选）", font=ctk.CTkFont(weight="bold")).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )
        ctk.CTkLabel(top, text="快捷选择：").grid(row=7, column=0, sticky="w", pady=5)
        self.option_templates = ctk.CTkOptionMenu(
            top,
            values=["(空)"],
            command=self._on_template_selected,
            width=360,
        )
        self.option_templates.grid(row=7, column=1, sticky="ew", padx=5, pady=5)
        lib_btns = ctk.CTkFrame(top)
        lib_btns.grid(row=7, column=2, sticky="ew", pady=5)
        ctk.CTkButton(lib_btns, text="加入模板库", command=self._add_template_to_library).grid(row=0, column=0, padx=2)
        ctk.CTkButton(lib_btns, text="打开目录", command=self._open_template_library_folder).grid(row=0, column=1, padx=2)
        ctk.CTkButton(lib_btns, text="删除选中", command=self._delete_selected_template).grid(row=0, column=2, padx=2)
        ctk.CTkButton(lib_btns, text="设置库目录", command=self._choose_template_library_root).grid(row=0, column=3, padx=2)
        self.lbl_library_root = ctk.CTkLabel(
            top, text="", text_color="gray60", anchor="w", justify="left", wraplength=900
        )
        self.lbl_library_root.grid(row=8, column=0, columnspan=3, sticky="ew", padx=(0, 5), pady=(0, 2))
        self.lbl_library_hint = ctk.CTkLabel(
            top,
            text="小提示：先在「模板 B」里选好文件，再点「加入模板库」；下拉框里出现名字后，点一下即可自动填路径。",
            text_color="gray60",
            anchor="w",
            justify="left",
            wraplength=900,
        )
        self.lbl_library_hint.grid(row=9, column=0, columnspan=3, sticky="ew", padx=(0, 5), pady=(0, 8))

        # 按钮区
        ctk.CTkLabel(top, text="【第4步】输出位置（生成的 Word 放哪里）", font=ctk.CTkFont(weight="bold")).grid(
            row=10, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )
        ctk.CTkLabel(top, text="输出目录：").grid(row=11, column=0, sticky="w", pady=(6, 4))
        self.lbl_output_root = ctk.CTkLabel(
            top, text="", text_color="gray60", anchor="w", justify="left", wraplength=900
        )
        self.lbl_output_root.grid(row=11, column=1, sticky="ew", padx=5, pady=(6, 4))
        out_btns = ctk.CTkFrame(top)
        out_btns.grid(row=11, column=2, sticky="e", pady=(6, 4))
        ctk.CTkButton(out_btns, text="设置输出目录", command=self._choose_output_dir).grid(row=0, column=0, padx=2)
        ctk.CTkButton(out_btns, text="打开输出目录", command=self._open_output_folder).grid(row=0, column=1, padx=2)

        step56_bar = ctk.CTkFrame(top, fg_color=("#1e3a5f", "#1e3a5f"), corner_radius=8)
        step56_bar.grid(row=12, column=0, columnspan=3, sticky="ew", pady=(14, 8))
        step56_bar.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            step56_bar,
            text="【第5～6步】先点下面左边按钮「开始提取」，再点右边「生成文档」",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=10)

        btn_frame = ctk.CTkFrame(top)
        btn_frame.grid(row=13, column=0, columnspan=3, sticky="ew", pady=(0, 4))
        btn_frame.columnconfigure((0, 1), weight=1)

        self.btn_extract = ctk.CTkButton(
            btn_frame,
            text="⑤ 1. 开始提取（读材料，稍等）",
            command=self._on_extract_clicked,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.btn_extract.grid(row=0, column=0, padx=5, sticky="ew")

        self.btn_render = ctk.CTkButton(
            btn_frame,
            text="⑥ 2. 生成文档（得到新 Word）",
            command=self._on_render_clicked,
            state="disabled",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.btn_render.grid(row=0, column=1, padx=5, sticky="ew")

        # 日志 / JSON 区域
        bottom = ctk.CTkFrame(self)
        bottom.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        bottom.rowconfigure(0, weight=1)
        bottom.columnconfigure((0, 1), weight=1)

        # 日志
        log_frame = ctk.CTkFrame(bottom)
        log_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        log_frame.rowconfigure(1, weight=1)
        ctk.CTkLabel(log_frame, text="运行日志（出错时可截图发给技术支持）").grid(row=0, column=0, sticky="w")
        self.txt_log = ctk.CTkTextbox(log_frame, wrap="word")
        self.txt_log.grid(row=1, column=0, sticky="nsew", pady=5)

        # JSON 结果
        json_frame = ctk.CTkFrame(bottom)
        json_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        json_frame.rowconfigure(4, weight=1)
        json_frame.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            json_frame,
            text="提取结果（可改字；点「2. 生成文档」时按这里的内容写入模板）",
            wraplength=420,
            anchor="w",
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.lbl_status = ctk.CTkLabel(json_frame, text="状态：空闲", text_color="gray70")
        self.lbl_status.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.progress = ctk.CTkProgressBar(json_frame, mode="indeterminate")
        self.progress.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        self.progress.set(0)
        self.progress.stop()
        self.lbl_mapping = ctk.CTkLabel(json_frame, text="匹配报告：未运行")
        self.lbl_mapping.grid(row=3, column=0, sticky="w", pady=(4, 0))
        self.txt_json = ctk.CTkTextbox(json_frame, wrap="word")
        self.txt_json.grid(row=4, column=0, sticky="nsew", pady=5)

    def _startup_health_check(self) -> None:
        """TRD：首次启动轻量探测模型服务（后台线程，不阻塞界面）。"""
        try:
            settings = CredentialProvider().load_settings()
            result = probe_llm(settings, timeout_sec=8)

            def _apply() -> None:
                self._log(f"[启动检查] {result.message}")
                if not result.ok and not result.skipped:
                    self._logger.warning("启动检查：模型服务不可用")

            self.after(0, _apply)
        except Exception as e:  # noqa: BLE001
            self.after(0, lambda: self._log(f"[启动检查] 异常：{e}"))

    def _bind_scroll_mousewheel(self, scroll_frame: ctk.CTkScrollableFrame) -> None:
        """Windows 下确保在可滚动区域上滚轮生效（部分主题/版本需显式绑定）。"""
        # Canvas 每次 yview_scroll(..., "units") 位移很小，只滚 1 单位会非常慢，这里放大步长
        _wheel_lines_per_notch = 50

        try:
            canvas = getattr(scroll_frame, "_parent_canvas", None)
            if canvas is None:
                return

            def _on_wheel(event: object) -> str:
                delta = getattr(event, "delta", 0) or 0
                steps = int(round(-(delta / 120.0) * _wheel_lines_per_notch))
                if steps != 0:
                    canvas.yview_scroll(steps, "units")
                return "break"

            def _bind_to_mousewheel(_evt: object) -> None:
                canvas.bind_all("<MouseWheel>", _on_wheel)

            def _unbind_from_mousewheel(_evt: object) -> None:
                canvas.unbind_all("<MouseWheel>")

            scroll_frame.bind("<Enter>", _bind_to_mousewheel)
            scroll_frame.bind("<Leave>", _unbind_from_mousewheel)
        except Exception:
            pass

    # 文件选择
    def _choose_source(self) -> None:
        path = filedialog.askopenfilename(
            title="选择源文档 A",
            filetypes=[("Word/PDF", "*.docx;*.pdf"), ("全部文件", "*.*")],
        )
        if path:
            self.entry_source.delete(0, "end")
            self.entry_source.insert(0, path)

    def _choose_template(self) -> None:
        path = filedialog.askopenfilename(
            title="选择模板文档 B",
            filetypes=[("Word 模板", "*.docx"), ("全部文件", "*.*")],
        )
        if path:
            self.entry_template.delete(0, "end")
            self.entry_template.insert(0, path)

    def _refresh_output_path_label(self) -> None:
        p = self._user_settings.get_output_dir()
        src = "环境变量" if os.getenv("AUTO_FILL_OUTPUT_DIR") else "已保存设置/默认"
        self.lbl_output_root.configure(text=f"（{src}）{p}")

    def _choose_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="选择生成文档（Word）的保存文件夹")
        if not folder:
            return
        try:
            self._user_settings.set_output_dir(folder)
            self._refresh_output_path_label()
            self._log(f"输出目录已设为：{self._user_settings.get_output_dir()}")
        except Exception as e:  # noqa: BLE001
            self._handle_error(f"设置输出目录失败：{e}")

    def _open_output_folder(self) -> None:
        folder = str(self._user_settings.get_output_dir())
        try:
            os.startfile(folder)  # type: ignore[attr-defined]
        except Exception as e:  # noqa: BLE001
            self._handle_error(f"无法打开目录：{e}")

    def _refresh_template_library_path_label(self) -> None:
        root = self._template_library.get_library_root()
        src = "环境变量" if os.getenv("AUTO_FILL_TEMPLATE_LIBRARY") else "已保存设置"
        self.lbl_library_root.configure(text=f"模板库目录（{src}）：{root}")

    def _choose_template_library_root(self) -> None:
        folder = filedialog.askdirectory(title="选择模板库存放文件夹（可放在 D/E 盘等）")
        if not folder:
            return
        try:
            self._user_settings.set_template_library_root(folder)
            self._template_library.reload_root()
            self._refresh_template_library_path_label()
            self._refresh_template_library()
            messagebox.showinfo(
                "已设置",
                "模板库目录已更新。\n"
                "新目录下的列表可能为空，请把常用模板重新「加入模板库」一次。\n"
                "（原目录里的文件不会被自动搬迁。）",
            )
            self._log(f"模板库目录已设为：{self._template_library.get_library_root()}")
        except Exception as e:  # noqa: BLE001
            self._handle_error(f"设置模板库目录失败：{e}")

    def _refresh_template_library(self) -> None:
        self._template_items = self._template_library.list_templates()
        display = []
        for item in self._template_items:
            display.append(f"{item.name}  ({Path(item.path).name})")
        if not display:
            display = ["(空)"]
        self.option_templates.configure(values=display)
        self.option_templates.set(display[0])
        self._selected_template_id = self._template_items[0].id if self._template_items else None

    def _on_template_selected(self, display_value: str) -> None:
        if not self._template_items:
            return
        # 通过 display_value 在列表中定位索引
        values = self.option_templates.cget("values")
        try:
            idx = list(values).index(display_value)
        except Exception:
            idx = 0
        idx = max(0, min(idx, len(self._template_items) - 1))
        item = self._template_items[idx]
        self._selected_template_id = item.id
        if not Path(item.path).exists():
            self._log("所选模板文件不存在，已自动刷新模板库。")
            self._refresh_template_library()
            return
        self.entry_template.delete(0, "end")
        self.entry_template.insert(0, item.path)
        self._log(f"已选择模板库模板：{item.name}")

    def _add_template_to_library(self) -> None:
        # 以当前 entry_template 作为来源加入模板库
        current = self.entry_template.get().strip()
        if not current:
            messagebox.showwarning("提示", "请先选择一个模板文件，再加入模板库。")
            return
        try:
            before = {x.path for x in self._template_items}
            item = self._template_library.add_template(current)
            after = {x.path for x in self._template_library.list_templates()}
            if item.path in before or len(after) == len(before):
                self._log(f"模板已存在于模板库：{item.name}")
            else:
                self._log(f"已加入模板库：{item.name}")
            self._refresh_template_library()
        except Exception as e:  # noqa: BLE001
            self._handle_error(f"加入模板库失败：{e}")

    def _open_template_library_folder(self) -> None:
        folder = self._template_library.open_library_folder()
        try:
            import os
            os.startfile(folder)  # type: ignore[attr-defined]
        except Exception as e:  # noqa: BLE001
            self._handle_error(f"无法打开目录：{e}")

    def _delete_selected_template(self) -> None:
        if not self._template_items or not self._selected_template_id:
            messagebox.showinfo("提示", "模板库为空或未选择模板。")
            return
        if not messagebox.askyesno("确认删除", "确定从模板库删除当前选中的模板吗？（不会影响你的原始文件）"):
            return
        try:
            self._template_library.remove_template(self._selected_template_id)
            self._log("已删除模板库模板。")
            self._refresh_template_library()
        except Exception as e:  # noqa: BLE001
            self._handle_error(f"删除失败：{e}")

    # 日志工具
    def _log(self, msg: str) -> None:
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self._logger.info(msg)

    def _apply_progress(self, msg: str) -> None:
        self.lbl_status.configure(text=f"状态：{msg}")
        self._log(msg)

    def _schedule_progress(self, msg: str) -> None:
        self.after(0, lambda m=msg: self._apply_progress(m))

    def _schedule_heartbeat(self, elapsed_sec: int) -> None:
        self.after(0, lambda s=elapsed_sec: self.lbl_status.configure(text=f"状态：调用模型中…已等待 {s}s"))

    def _set_buttons_state(self, extracting: bool = False) -> None:
        if extracting:
            self.btn_extract.configure(state="disabled")
            self.btn_render.configure(state="disabled")
            self.progress.start()
            self.lbl_status.configure(text="状态：处理中…")
        else:
            self.btn_extract.configure(state="normal")
            self.btn_render.configure(state="normal" if self._json_data else "disabled")
            self.progress.stop()
            self.progress.set(0)
            self.lbl_status.configure(text="状态：空闲")

    # 事件处理
    def _on_extract_clicked(self) -> None:
        source = self.entry_source.get().strip()
        template = self.entry_template.get().strip()
        if not source or not template:
            messagebox.showwarning("提示", "请先选择源文档 A 和模板文档 B。")
            return

        self._log(f"开始提取：A={source}, B={template}")
        self._set_buttons_state(extracting=True)

        # 先把“模板字段骨架 JSON”展示到右侧，确保用户等待时可视化
        try:
            keys = self._scanner.scan(template)
        except Exception:
            keys = []
        if keys:
            import json as _json

            skeleton = {k: "" for k in keys}
            self.txt_json.delete("1.0", "end")
            self.txt_json.insert("1.0", _json.dumps(skeleton, ensure_ascii=False, indent=2))
            self.lbl_mapping.configure(text=f"匹配报告：已扫描字段 {len(keys)}（等待模型返回）")
        else:
            self.txt_json.delete("1.0", "end")
            self.txt_json.insert("1.0", "{\n  \n}")
            self.lbl_mapping.configure(text="匹配报告：未扫描到 {{变量}}（请确认模板是否为成品模板）")

        threading.Thread(
            target=self._do_extract_thread, args=(source, template), daemon=True
        ).start()

    def _do_extract_thread(self, source: str, template: str) -> None:
        try:
            json_data, report, expected_keys = self._wf.run_extract(
                source,
                template,
                progress_callback=self._schedule_progress,
                heartbeat_callback=self._schedule_heartbeat,
                stream_callback=lambda chunk: self.after(0, lambda c=chunk: self._append_stream_chunk(c)),
                raw_callback=lambda raw: self.after(0, lambda r=raw: self._show_raw_output(r)),
            )
            self._json_data = json_data
            self._expected_keys = expected_keys
            self._mapping = report.model_dump()

            import json as _json

            pretty = _json.dumps(json_data, ensure_ascii=False, indent=2)

            def update_ui() -> None:
                self._log("提取完成。")
                self._log(f"模板字段数：{len(expected_keys)}")
                self._log(
                    f"匹配结果：matched={len(report.matched)}, missing={len(report.missing_in_json)}, "
                    f"extra={len(report.extra_in_json)}, 值为空={len(report.value_empty)}"
                )
                if report.value_empty:
                    preview = "、".join(report.value_empty[:8])
                    if len(report.value_empty) > 8:
                        preview += "…"
                    self._log(f"值为空字段（请核对或手工填写）：{preview}")
                self.txt_json.delete("1.0", "end")
                self.txt_json.insert("1.0", pretty)
                self.lbl_mapping.configure(
                    text=(
                        f"匹配报告：matched={len(report.matched)} | missing={len(report.missing_in_json)} "
                        f"| extra={len(report.extra_in_json)} | 空值={len(report.value_empty)}"
                    )
                )
                self._set_buttons_state(extracting=False)

            self.after(0, update_ui)
        except AutoFillError as e:
            self._logger.exception("提取失败")
            self.after(0, lambda: self._handle_error(str(e)))
        except Exception as e:  # noqa: BLE001
            self._logger.exception("提取未知失败")
            self.after(0, lambda: self._handle_error(f"未知错误：{e}"))

    def _on_render_clicked(self) -> None:
        # 以右侧 JSON 文本框内容为准（允许用户手工修正）
        import json as _json
        raw = self.txt_json.get("1.0", "end").strip()
        if not raw:
            messagebox.showwarning("提示", "右侧 JSON 为空，请先提取或手工填写 JSON。")
            return
        try:
            self._json_data = _json.loads(raw)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("错误", f"JSON 格式不合法：{e}")
            return

        template = self.entry_template.get().strip()
        if not template:
            messagebox.showwarning("提示", "请先选择模板文档 B。")
            return

        out_dir = self._user_settings.get_output_dir()
        out_dir_str = str(out_dir)
        self._log(f"开始渲染，输出目录：{out_dir_str}")
        self._set_buttons_state(extracting=True)

        threading.Thread(
            target=self._do_render_thread,
            args=(template, out_dir_str),
            daemon=True,
        ).start()

    def _do_render_thread(self, template: str, out_dir: str) -> None:
        try:
            output_path = self._wf.run_render(template, self._json_data, out_dir, require_all_keys=False)

            def update_ui() -> None:
                self._log(f"渲染完成：{output_path}")
                messagebox.showinfo("成功", f"生成文档成功：\n{output_path}")
                self._set_buttons_state(extracting=False)

            self.after(0, update_ui)
        except AutoFillError as e:
            self._logger.exception("渲染失败")
            self.after(0, lambda: self._handle_error(str(e)))
        except Exception as e:  # noqa: BLE001
            self._logger.exception("渲染未知失败")
            self.after(0, lambda: self._handle_error(f"未知错误：{e}"))

    def _handle_error(self, msg: str) -> None:
        self._log(f"错误：{msg}")
        messagebox.showerror("错误", msg)
        self._set_buttons_state(extracting=False)

    def _append_stream_chunk(self, chunk: str) -> None:
        # 将模型流式输出展示到右侧文本框（节流：批量刷新）
        if not chunk:
            return
        self._stream_buffer.append(chunk)
        if self._stream_flush_scheduled:
            return
        self._stream_flush_scheduled = True
        self.after(50, self._flush_stream_buffer)

    def _flush_stream_buffer(self) -> None:
        self._stream_flush_scheduled = False
        if not self._stream_buffer:
            return
        text = "".join(self._stream_buffer)
        self._stream_buffer.clear()
        self.txt_json.insert("end", text)
        self.txt_json.see("end")

    def _show_raw_output(self, raw: str) -> None:
        # 无论是否流式可用，只要模型返回，就先把 raw 放到右侧，避免“空白等待”
        if not raw:
            return
        # raw 覆盖时清空流式缓冲，避免后续 flush 把旧 chunk 追加回来
        self._stream_buffer.clear()
        self._stream_flush_scheduled = False
        self.txt_json.delete("1.0", "end")
        self.txt_json.insert("1.0", raw)
        self.txt_json.see("end")


def run_app() -> None:
    app = AppWindow()
    app.mainloop()

