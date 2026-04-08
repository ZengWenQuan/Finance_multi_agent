from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPORT_DIR = Path(__file__).resolve().parent / "report"


def ensure_report_dir() -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return REPORT_DIR


def save_agent_report(agent_name: str, content: str, metadata: dict[str, Any] | None = None) -> Path:
    report_dir = ensure_report_dir()
    report_path = report_dir / f"{agent_name}.md"
    report_path.write_text(content or "", encoding="utf-8")

    if metadata is not None:
        metadata_path = report_dir / f"{agent_name}.json"
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return report_path
