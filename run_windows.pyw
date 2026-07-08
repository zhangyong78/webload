from __future__ import annotations

import traceback
from pathlib import Path

from flash_earn_reminder.ui import run


def _log_error(text: str) -> None:
    Path("data").mkdir(parents=True, exist_ok=True)
    Path("data/launcher_error.log").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except SystemExit:
        raise
    except Exception:
        _log_error(traceback.format_exc())
        raise
