from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


def _appdata_autofill() -> Path:
    appdata = os.getenv("APPDATA") or str(Path.home())
    return Path(appdata) / "AutoFill"


class UserSettings(BaseModel):
    """用户可改配置（非密钥）；密钥仍走环境变量。"""

    template_library_root: str = Field(default="")
    output_dir: str = Field(default="")


class UserSettingsStore:
    """
    持久化路径：%APPDATA%/AutoFill/settings.json
    模板库根目录优先读环境变量 AUTO_FILL_TEMPLATE_LIBRARY，其次读 settings。
    输出目录优先读环境变量 AUTO_FILL_OUTPUT_DIR，其次读 settings。
    """

    ENV_TEMPLATE_LIBRARY = "AUTO_FILL_TEMPLATE_LIBRARY"
    ENV_OUTPUT_DIR = "AUTO_FILL_OUTPUT_DIR"

    def __init__(self) -> None:
        self._path = _appdata_autofill() / "settings.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> UserSettings:
        if not self._path.exists():
            return UserSettings()
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return UserSettings(**data)
        except Exception:
            return UserSettings()

    def save(self, settings: UserSettings) -> None:
        self._path.write_text(
            json.dumps(settings.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_template_library_root(self) -> Path:
        env = (os.getenv(self.ENV_TEMPLATE_LIBRARY) or "").strip()
        if env:
            return Path(env)
        s = self.load()
        if (s.template_library_root or "").strip():
            return Path(s.template_library_root.strip())
        # 默认：项目当前工作目录下的 template_library（通常即 E:\AutoFill\template_library），避免占用 C 盘
        return Path.cwd() / "template_library"

    def set_template_library_root(self, folder: str) -> None:
        p = Path(folder).resolve()
        p.mkdir(parents=True, exist_ok=True)
        s = self.load()
        s.template_library_root = str(p)
        self.save(s)

    def get_output_dir(self) -> Path:
        env = (os.getenv(self.ENV_OUTPUT_DIR) or "").strip()
        if env:
            p = Path(env)
        else:
            s = self.load()
            if (s.output_dir or "").strip():
                p = Path(s.output_dir.strip())
            else:
                p = Path.cwd() / "outputs"
        p.mkdir(parents=True, exist_ok=True)
        return p.resolve()

    def set_output_dir(self, folder: str) -> None:
        p = Path(folder).resolve()
        p.mkdir(parents=True, exist_ok=True)
        s = self.load()
        s.output_dir = str(p)
        self.save(s)
