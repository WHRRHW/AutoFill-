from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class OutputNameOptions:
    time_format: str = "%Y%m%d_%H%M%S"
    suffix: str = "_filled"


class OutputNamer:
    def build_output_path(self, template_path: str, output_dir: str, options: OutputNameOptions | None = None) -> str:
        options = options or OutputNameOptions()
        tpl = Path(template_path)
        out_dir = Path(output_dir)
        ts = datetime.now().strftime(options.time_format)
        name = f"{tpl.stem}{options.suffix}_{ts}{tpl.suffix}"
        return str(out_dir / name)

