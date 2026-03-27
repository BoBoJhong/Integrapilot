"""啟動 Web 介面（FastAPI + Vue 靜態頁）。"""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("web_api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
