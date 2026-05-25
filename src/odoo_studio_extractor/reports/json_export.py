"""JSON export of the raw extracted dataset."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_report(data: dict[str, Any], path: Path | str) -> Path:
    """Write ``data`` as pretty-printed UTF-8 JSON.

    Returns the absolute path of the file written.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, default=str, sort_keys=False)
        fh.write("\n")
    return out.resolve()
