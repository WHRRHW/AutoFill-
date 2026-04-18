from __future__ import annotations

from app.infrastructure.config.settings import Settings
from app.infrastructure.health import probe_llm


def test_probe_llm_skipped_when_no_credentials() -> None:
    s = Settings(api_key="", api_base_url="")
    r = probe_llm(s, timeout_sec=1)
    assert r.skipped is True
    assert r.ok is True
    assert "跳过" in r.message
