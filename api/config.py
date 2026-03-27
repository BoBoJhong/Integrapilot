"""路徑與常數（相對於專案根目錄）。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# 專案根：api/ 的上一層
BASE_DIR = Path(__file__).resolve().parent.parent

REPORTS_DIR = BASE_DIR / "reports"
UPLOAD_DIR = BASE_DIR / "uploads"
UI_DIR = BASE_DIR / "ui"
UI_DIST = UI_DIR / "dist"
AGENTS_FILE = BASE_DIR / "agents.json"

LIST_DIR_MAX_ENTRIES = 500


def setup_env() -> None:
    load_dotenv()


def setup_dirs() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
