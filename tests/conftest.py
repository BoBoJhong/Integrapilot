"""Pytest 設定：預設關閉 API 速率限制以利測試。"""

import os

os.environ.setdefault("DISABLE_RATE_LIMIT", "1")
