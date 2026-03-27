# --- 前端：Vue 3 + Vite 建置 ---
FROM node:20-bookworm-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- 後端：Python + CrewAI ---
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git pandoc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY integrapilot ./integrapilot
COPY api ./api
COPY run.py .
COPY web_api.py .
COPY word_reference.py .
COPY run_web.py .
COPY --from=frontend-build /app/ui/dist ./ui/dist
RUN mkdir -p /app/reports /app/uploads && python -c "from pathlib import Path; from word_reference import build_word_reference_docx; build_word_reference_docx(Path('assets/word-reference.docx'))"
VOLUME ["/app/reports", "/app/uploads"]

# Web UI：開啟 http://localhost:8000
# docker run --rm -p 8000:8000 -v ... --env-file .env integrapilot
CMD ["python", "run_web.py"]
