"""FastAPI 服務：提供 Vue UI 與 CrewAI 評估 API。

uvicorn：`uvicorn web_api:app` 或 `python run_web.py`
"""

from __future__ import annotations

from api.main import create_app

app = create_app()
