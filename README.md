# IntegraPilot

IntegraPilot 是一個以 CrewAI 驅動的雙專案整合評估工具，提供 CLI 與 Web UI（FastAPI + Vue 3），用來比較兩個專案、產生整合建議報告，並透過 Agent 對話協助決策下一步。

## 特色

- 雙專案整合評估：比較專案 A / B，產出 Markdown 報告
- 報告工作台：報告列表、預覽、下載、Word 匯出
- Agent 對話：依報告內容追問、釐清風險與行動建議
- 決策選項助手：產生方案、勾選排序、綜合建議、套用回報告
- 專案來源：路徑輸入、ZIP 上傳、Git HTTPS clone
- 前端工程化：Pinia + TanStack Query + Zod

## 專案結構

```text
.
├─ api/                    # FastAPI 路由、schema、helper
├─ integrapilot/           # CrewAI agents/tasks（Python 套件目錄）
├─ frontend/               # Vue 3 + Vite + Element Plus
│  ├─ src/stores/          # Pinia store
│  └─ src/api/             # API client + Zod schema
├─ docs/                   # UI 規格與 roadmap
├─ reports/                # 產生的報告檔
├─ uploads/                # ZIP/clone 暫存
├─ run.py                  # CLI 入口
├─ run_web.py              # Web 入口
└─ dockerfile              # 多階段建置
```

## 環境需求

- Python 3.12+
- Node.js 20+
- （可選）Docker
- `GOOGLE_API_KEY`（必填）

### 本機資料夾名稱（建議）

建議將專案根目錄命名為 **`integrapilot`**，與 Docker 映像 **`integrapilot`**、容器 **`integrapilot-web`** 一致。若 IDE 正在使用該資料夾導致無法重新命名，請先關閉工作區後再於檔案總管改名。

## 本機啟動

### 後端

```bash
pip install -r requirements.txt
python run_web.py
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## Docker

```bash
docker build -t integrapilot .
docker run --rm -p 8000:8000 --env-file .env --name integrapilot-web integrapilot
```

## 主要 API

- `POST /api/assess`
- `GET /api/reports`
- `GET /api/reports/{report_id}`
- `POST /api/chat`
- `POST /api/options/generate`
- `POST /api/options/synthesize`
- `POST /api/reports/{report_id}/patch`

## 常見問題

- Docker 內路徑請使用容器路徑（如 `/projA`、`/projB`），不要直接填 `C:\...`
- `422 query.payload` 通常是請求格式錯誤，請確認使用 `POST` 並帶 `Content-Type: application/json`
