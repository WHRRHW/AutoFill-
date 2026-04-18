from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.domain.errors import SourceReadError
from app.infrastructure.config.user_settings import UserSettingsStore


@dataclass(frozen=True)
class TemplateItem:
    id: str
    name: str
    path: str
    created_at: str
    digest_sha256: str = ""


class TemplateLibrary:
    """
    模板库：
    - 根目录优先：环境变量 AUTO_FILL_TEMPLATE_LIBRARY
    - 其次：%APPDATA%/AutoFill/settings.json 中的 template_library_root
    - 默认：当前工作目录下的 template_library/（便于放在 E 盘等项目盘）
    """

    def __init__(self, store: Optional[UserSettingsStore] = None) -> None:
        self._store = store or UserSettingsStore()
        self._root: Path = Path()
        self._index_path: Path = Path()
        self._apply_root(self._store.get_template_library_root())

    def _apply_root(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._index_path = self._root / "library.json"

    def reload_root(self) -> None:
        """用户修改模板库目录后调用。"""
        self._apply_root(self._store.get_template_library_root())

    def get_library_root(self) -> str:
        return str(self._root.resolve())

    def list_templates(self) -> List[TemplateItem]:
        data = self._load_index()
        items = []
        changed = False
        for x in data.get("items", []):
            if "digest_sha256" not in x:
                x["digest_sha256"] = ""
                changed = True
            p = Path(x.get("path", ""))
            if not p.exists():
                changed = True
                continue
            items.append(TemplateItem(**x))

        if changed:
            data["items"] = [i.__dict__ for i in items]
            self._save_index(data)

        return items

    def add_template(self, source_docx_path: str, name: Optional[str] = None) -> TemplateItem:
        src = Path(source_docx_path)
        if not src.exists():
            raise SourceReadError(f"模板文件不存在：{source_docx_path}")
        if src.suffix.lower() != ".docx":
            raise SourceReadError("模板库仅支持 .docx 模板文件")

        digest = self._sha256_file(src)
        index = self._load_index()
        items = index.get("items", [])
        for x in items:
            if x.get("digest_sha256") == digest and Path(x.get("path", "")).exists():
                return TemplateItem(**x)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = (name or src.stem).strip() or src.stem
        item_id = f"{safe_name}_{ts}"
        dst = self._root / f"{item_id}{src.suffix}"

        shutil.copy2(str(src), str(dst))

        item = TemplateItem(
            id=item_id,
            name=safe_name,
            path=str(dst),
            created_at=datetime.now().isoformat(timespec="seconds"),
            digest_sha256=digest,
        )

        items.append(item.__dict__)
        index["items"] = items
        self._save_index(index)
        return item

    def remove_template(self, item_id: str) -> None:
        index = self._load_index()
        items = index.get("items", [])
        kept = []
        removed_path = None
        for x in items:
            if x.get("id") == item_id:
                removed_path = x.get("path")
            else:
                kept.append(x)
        index["items"] = kept
        self._save_index(index)

        if removed_path:
            try:
                Path(removed_path).unlink(missing_ok=True)
            except Exception:
                pass

    def open_library_folder(self) -> str:
        return str(self._root.resolve())

    def _load_index(self) -> dict:
        if not self._index_path.exists():
            return {"items": []}
        try:
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        except Exception:
            return {"items": []}

    def _save_index(self, data: dict) -> None:
        self._index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _sha256_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
