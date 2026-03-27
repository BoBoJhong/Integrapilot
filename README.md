# IntegraPilot

IntegraPilot 是一個以 CrewAI 驅動的雙專案整合評估工具，提供 CLI 與 Web UI（FastAPI + Vue 3），用來比較兩個專案、產生整合建議報告，並透過 Agent 對話協助決策下一步。

## 特色

- 雙輸入整合評估：比較 A / B（可目錄對目錄、檔案對檔案、檔案對目錄），產出 Markdown 報告
- 報告工作台：報告列表、預覽、下載、Word 匯出
- Agent 對話：依報告內容追問、釐清風險與行動建議
- 決策選項助手：產生方案、勾選排序、綜合建議、套用回報告
- 專案來源：路徑輸入、ZIP 上傳、Git HTTPS clone
- 前端工程化：Pinia + TanStack Query + Zod

## 專案結構

```text
.
├─ .github/workflows/      # GitHub Actions（CI/CD）
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

## 環境變數

基本：

- `GOOGLE_API_KEY`：Gemini API 金鑰（必填）
- `MODEL`：LiteLLM 模型名稱（預設 `gemini/gemini-2.5-flash`）
- `DATABASE_URL`：資料庫連線字串（建議 PostgreSQL）

評估輸入上限（選填）：

- `ASSESS_MAX_TREE_ENTRIES`：目錄摘要最多列出幾筆路徑（預設 `250`）
- `ASSESS_MAX_KEY_FILES`：最多擷取幾個關鍵檔內容（預設 `30`）
- `ASSESS_MAX_FILE_CHARS`：每個關鍵檔最多擷取字元數（預設 `4000`）
- `ASSESS_MAX_SNAPSHOT_CHARS`：單個專案摘要總字元上限（預設 `30000`）
- `ASSESS_MAX_EVIDENCE_FILES`：報告中列出的引用檔案上限（預設 `25`）

設定為 `0` 或 `-1` 代表該項「不限制」（仍受模型 token 上限影響，且可能提高成本與延遲）。

### 本機資料夾名稱（建議）

建議將專案根目錄命名為 **`integrapilot`**，與 Docker 映像 **`integrapilot`**、容器 **`integrapilot-web`** 一致。若 IDE 正在使用該資料夾導致無法重新命名，請先關閉工作區後再於檔案總管改名。

## 本機啟動

### 後端

```bash
pip install -r requirements.txt
python run_web.py
```

### CLI（目錄或檔案）

```bash
python run.py --project-a /projA --project-b /projB
python run.py --project-a /projA/src/main.py --project-b /projB/src/main.py
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

### Docker Compose（含 PostgreSQL）

```bash
docker compose up -d --build
```

預設會把專案根目錄的 `projA/`、`projB/` 自動掛到容器內 `/projA`、`/projB`，可直接把要比對的檔案丟進這兩個資料夾後，在 UI 填 `/projA/...` 與 `/projB/...`。

首次導入舊資料（可選）：

```bash
docker exec -it integrapilot-web python -m api.migrations.seed_from_files
```

手動執行 migration（可選）：

```bash
docker exec -it integrapilot-web alembic upgrade head
```

## CI/CD（GitHub Actions）

專案已內建兩條 workflow：

- `CI`：在 `push main` 與 `pull_request` 觸發，執行：
  - Backend `pytest`
  - Frontend `npm run lint`、`npm run build`
  - Docker image build 檢查（不推送）
- `CD`：在 `push main`、`push tag (v*)` 或手動觸發時，建置並推送映像到 GHCR：
  - Image: `ghcr.io/<你的 GitHub 帳號或組織>/integrapilot`
  - 預設標籤包含 `latest`（預設分支）、branch、tag、sha

### 啟用 CD 必要設定

1. 確認 repository 的 Actions 權限允許寫入 packages（workflow 已設定 `packages: write`）
2. 若要使用版本標籤發版，建立並推送 tag（例如 `v1.0.0`）：

```bash
git tag v1.0.0
git push origin v1.0.0
```

## 主要 API

- `POST /api/assess`
- `GET /api/reports`
- `GET /api/reports/{report_id}`
- `POST /api/chat`
- `POST /api/options/generate`
- `POST /api/options/synthesize`
- `POST /api/reports/{report_id}/patch`

## 資料儲存策略

- 實體檔案維持路徑掛載與資料夾管理（`reports/`、`uploads/`、`/projA`、`/projB`）
- PostgreSQL 儲存中繼資料（reports、assessment jobs、agents、input assets）
- `/api/reports`、`/api/agents` 優先讀資料庫；可用 seed 指令匯入歷史檔案資料
- `POST /api/reports/{report_id}/patch` 產生的新報告也會同步寫入資料庫索引

## 常見問題

- Docker 內路徑請使用容器路徑（如 `/projA`、`/projB`），不要直接填 `C:\...`
- 若出現「不是有效路徑（檔案或目錄）」：代表容器內找不到該路徑，請確認 docker 掛載與輸入路徑（可用目錄或單一檔案）
- 報告檔名時間戳與 `updated_at` 皆以台北時區（`Asia/Taipei`, UTC+8）為準
- `422 query.payload` 通常是請求格式錯誤，請確認使用 `POST` 並帶 `Content-Type: application/json`
