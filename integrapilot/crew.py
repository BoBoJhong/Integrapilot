"""定義「兩專案整合評估」的 Agents、Tasks 與 Crew。"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from crewai import Agent, Crew, LLM, Process, Task
from dotenv import load_dotenv

MAX_TREE_ENTRIES = 250
MAX_KEY_FILES = 30
MAX_FILE_CHARS = 4000
MAX_SNAPSHOT_CHARS = 30000
MAX_EVIDENCE_FILES = 25

KEY_FILE_PATTERNS = [
    "README*",
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "requirements*.txt",
    "pyproject.toml",
    "poetry.lock",
    "go.mod",
    "go.sum",
    "pom.xml",
    "build.gradle*",
    "Cargo.toml",
    "Dockerfile*",
    "docker-compose*.yml",
    "docker-compose*.yaml",
    "*.env.example",
    "openapi*.yml",
    "openapi*.yaml",
]

IGNORE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
}


def _env_int_limit(name: str, default: int) -> int | None:
    """讀取整數上限；允許 0 或 -1 代表不限制。"""
    raw = os.getenv(name)
    if raw is None:
        return default

    text = raw.strip()
    if not text:
        return default
    if text in {"0", "-1"}:
        return None

    try:
        value = int(text)
    except ValueError:
        return default
    if value < 1:
        return default
    return value


def _load_assessment_limits() -> dict[str, int | None]:
    return {
        "max_tree_entries": _env_int_limit("ASSESS_MAX_TREE_ENTRIES", MAX_TREE_ENTRIES),
        "max_key_files": _env_int_limit("ASSESS_MAX_KEY_FILES", MAX_KEY_FILES),
        "max_file_chars": _env_int_limit("ASSESS_MAX_FILE_CHARS", MAX_FILE_CHARS),
        "max_snapshot_chars": _env_int_limit(
            "ASSESS_MAX_SNAPSHOT_CHARS", MAX_SNAPSHOT_CHARS
        ),
        "max_evidence_files": _env_int_limit(
            "ASSESS_MAX_EVIDENCE_FILES", MAX_EVIDENCE_FILES
        ),
    }


def _build_llm() -> LLM:
    load_dotenv()
    model = os.getenv("MODEL", "gemini/gemini-2.5-flash")
    return LLM(model=model)


def _is_key_file(name: str) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in KEY_FILE_PATTERNS)


def _build_project_snapshot(project_path: str, limits: dict[str, int | None]) -> str:
    root = Path(project_path)
    if not root.is_dir():
        return f"無效路徑：{project_path}"

    max_tree_entries = limits["max_tree_entries"]
    max_key_files = limits["max_key_files"]
    max_file_chars = limits["max_file_chars"]
    max_snapshot_chars = limits["max_snapshot_chars"]

    tree_lines: list[str] = []
    key_files: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        rel_dir = Path(dirpath).relative_to(root)

        for d in sorted(dirnames):
            if max_tree_entries is not None and len(tree_lines) >= max_tree_entries:
                break
            p = (rel_dir / d).as_posix()
            tree_lines.append(f"- {p}/")
        if max_tree_entries is not None and len(tree_lines) >= max_tree_entries:
            break

        for f in sorted(filenames):
            if max_tree_entries is not None and len(tree_lines) >= max_tree_entries:
                break
            p = rel_dir / f
            tree_lines.append(f"- {p.as_posix()}")
            if (
                _is_key_file(f)
                and (max_key_files is None or len(key_files) < max_key_files)
            ):
                key_files.append(Path(dirpath) / f)
        if max_tree_entries is not None and len(tree_lines) >= max_tree_entries:
            break

    parts: list[str] = []
    parts.append(f"專案根目錄：{root}")
    parts.append("\n## 目錄摘要（截斷版）")
    parts.append("\n".join(tree_lines) if tree_lines else "- （無可列目錄）")

    parts.append("\n## 關鍵檔內容節錄（截斷版）")
    if not key_files:
        parts.append("- 找不到常見關鍵檔（README/package.json/pyproject.toml 等）")
    else:
        for p in key_files:
            rel = p.relative_to(root).as_posix()
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError as e:
                parts.append(f"\n### {rel}\n（讀取失敗：{e}）")
                continue
            snippet = text if max_file_chars is None else text[:max_file_chars]
            if max_file_chars is not None and len(text) > max_file_chars:
                snippet += "\n...（已截斷）"
            parts.append(f"\n### {rel}\n```text\n{snippet}\n```")

    out = "\n".join(parts)
    if max_snapshot_chars is not None and len(out) > max_snapshot_chars:
        return out[:max_snapshot_chars] + "\n\n...（整體摘要已截斷）"
    return out


def _collect_project_evidence(
    project_path: str, limits: dict[str, int | None]
) -> dict[str, object]:
    """收集報告可展示的評估證據（關鍵檔與掃描統計）。"""
    root = Path(project_path)
    if not root.is_dir():
        return {
            "root": str(root),
            "is_valid": False,
            "scanned_dirs": 0,
            "scanned_files": 0,
            "key_files": [],
        }

    scanned_dirs = 0
    scanned_files = 0
    key_files: list[str] = []
    max_evidence_files = limits["max_evidence_files"]

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        scanned_dirs += 1

        for name in filenames:
            scanned_files += 1
            if max_evidence_files is not None and len(key_files) >= max_evidence_files:
                continue
            if _is_key_file(name):
                rel = (Path(dirpath) / name).relative_to(root).as_posix()
                key_files.append(rel)

    if not key_files:
        # 若沒有命中 pattern，至少提供幾個樣本檔案，讓評估來源可追蹤。
        samples: list[str] = []
        sample_limit = 10
        if max_evidence_files is not None:
            sample_limit = min(sample_limit, max_evidence_files)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            for name in sorted(filenames):
                rel = (Path(dirpath) / name).relative_to(root).as_posix()
                samples.append(rel)
                if len(samples) >= sample_limit:
                    break
            if len(samples) >= sample_limit:
                break
        key_files = samples

    return {
        "root": str(root),
        "is_valid": True,
        "scanned_dirs": scanned_dirs,
        "scanned_files": scanned_files,
        "key_files": key_files,
    }


def build_evaluation_trace_markdown(project_a_path: str, project_b_path: str) -> str:
    """輸出「如何評估、用了什麼檔案」的透明化區塊。"""
    limits = _load_assessment_limits()
    ev_a = _collect_project_evidence(project_a_path, limits)
    ev_b = _collect_project_evidence(project_b_path, limits)

    def _format_files(title: str, ev: dict[str, object]) -> list[str]:
        lines: list[str] = [f"### {title}"]
        lines.append(f"- 根目錄：`{ev['root']}`")
        lines.append(
            f"- 掃描統計：目錄 {ev['scanned_dirs']} 個、檔案 {ev['scanned_files']} 個"
        )
        files = ev.get("key_files", [])
        if not files:
            lines.append("- 關鍵檔：無")
            return lines
        lines.append("- 關鍵檔（節錄）:")
        for rel in files:
            lines.append(f"  - `{rel}`")
        return lines

    parts: list[str] = [
        "## 評估方式與引用檔案",
        "本次評估採用受控摘要流程，避免直接讀取整個專案造成噪音或 token 爆量。",
        "",
        "### 評估流程",
        "1. 掃描兩邊專案目錄（忽略 `.git`、`node_modules`、`dist`、`.venv` 等目錄）",
        "2. 篩選關鍵檔（例如 `README*`、`package.json`、`requirements*.txt`、`Dockerfile*`）",
        "3. 對關鍵檔進行截斷節錄，提供給分析 Agent 判斷技術棧與邊界",
        "4. 由整合架構 Agent 匯總成整合建議與風險",
        "",
    ]
    parts.extend(_format_files("專案 A 引用依據", ev_a))
    parts.append("")
    parts.extend(_format_files("專案 B 引用依據", ev_b))
    return "\n".join(parts)


def create_integration_assessment_crew(project_a_path: str, project_b_path: str) -> Crew:
    """建立依序執行的 Crew，使用受控摘要避免 token 過大。"""
    llm = _build_llm()
    limits = _load_assessment_limits()
    snapshot_a = _build_project_snapshot(project_a_path, limits)
    snapshot_b = _build_project_snapshot(project_b_path, limits)

    codebase_analyst = Agent(
        role="程式庫與結構分析師",
        goal="根據提供的專案摘要整理技術棧、模組邊界、對外介面與依賴關係。",
        backstory=(
            "你擅長從目錄結構與設定檔片段快速判斷框架、語言版本與建置方式，"
            "並指出可能與其他系統銜接的 API、事件、佇列或資料庫。"
        ),
        llm=llm,
        verbose=True,
    )

    integration_architect = Agent(
        role="整合架構師",
        goal="根據兩份專案摘要，評估整合方式、相容性與風險，並給出可執行建議。",
        backstory=(
            "你熟悉微服務、單體模組化、API 契約與資料同步，"
            "能區分「可直接共用」「需轉接層」「不建議硬整合」等情境。"
        ),
        llm=llm,
        verbose=True,
    )

    task_a = Task(
        description=(
            "分析專案 A 的摘要資訊，輸出結構化分析。\n\n"
            "輸出須包含：\n"
            "- 技術棧與執行／建置方式\n"
            "- 主要模組或服務邊界\n"
            "- 對外暴露的介面（HTTP、gRPC、訊息佇列、檔案、DB schema 等）\n"
            "- 與整合相關的注意事項（認證、版本、同步／非同步假設）\n\n"
            f"以下是專案 A 摘要：\n\n{snapshot_a}"
        ),
        expected_output="專案 A 的結構化 Markdown 摘要，標題清楚、條列為主。",
        agent=codebase_analyst,
    )

    task_b = Task(
        description=(
            "分析專案 B 的摘要資訊，並使用與專案 A 相同章節，以利比對。\n\n"
            f"以下是專案 B 摘要：\n\n{snapshot_b}"
        ),
        expected_output="專案 B 的結構化 Markdown 摘要，章節與專案 A 對齊。",
        agent=codebase_analyst,
        context=[task_a],
    )

    task_integrate = Task(
        description=(
            "根據「專案 A」與「專案 B」的分析結果，撰寫「整合評估報告」。\n\n"
            "報告須包含：\n"
            "1. 執行摘要（是否適合整合、一句話結論）\n"
            "2. 對齊點：可重用的協定、資料模型、認證方式\n"
            "3. 落差與摩擦點：語言／框架／部署／資料格式不一致處\n"
            "4. 整合選項：至少兩種（例如 API 閘道、共用函式庫、事件匯流排、ETL）與取捨\n"
            "5. 風險清單（依嚴重度排序）與緩解方式\n"
            "6. 建議的階段性里程碑（MVP -> 擴充）\n"
        ),
        expected_output="完整 Markdown 整合評估報告，可直接給技術負責人與 PM 閱讀。",
        agent=integration_architect,
        context=[task_a, task_b],
    )

    return Crew(
        agents=[codebase_analyst, integration_architect],
        tasks=[task_a, task_b, task_integrate],
        process=Process.sequential,
        verbose=True,
    )
