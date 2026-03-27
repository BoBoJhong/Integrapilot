"""業務邏輯與檔案／路徑／匯出等輔助函式。"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile

from word_reference import ensure_word_reference_docx

from api.config import (
    AGENTS_FILE,
    LIST_DIR_MAX_ENTRIES,
    REPORTS_DIR,
    UPLOAD_DIR,
)


def _report_filename(project_a: str, project_b: str) -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    a_name = Path(project_a).name or "project_a"
    b_name = Path(project_b).name or "project_b"
    safe = re.compile(r"[^a-zA-Z0-9._-]")
    a_name = safe.sub("_", a_name)[:40]
    b_name = safe.sub("_", b_name)[:40]
    return f"{ts}__{a_name}__vs__{b_name}.md"


def save_report(project_a: str, project_b: str, content: str) -> str:
    filename = _report_filename(project_a, project_b)
    report_path = REPORTS_DIR / filename
    report_path.write_text(content, encoding="utf-8")
    return filename


def build_llm():
    from crewai import LLM

    model = os.getenv("MODEL", "gemini/gemini-2.5-flash")
    return LLM(model=model)


def load_report_text(report_id: str | None) -> str:
    if not report_id:
        return ""
    if "/" in report_id or "\\" in report_id or ".." in report_id:
        raise HTTPException(status_code=400, detail="無效的 report_id")
    target = REPORTS_DIR / report_id
    if not target.is_file():
        raise HTTPException(status_code=404, detail="找不到報告")
    return target.read_text(encoding="utf-8")


def history_to_text(history: list[dict[str, str]], max_turns: int = 8) -> str:
    lines: list[str] = []
    for item in history[-max_turns:]:
        role = item.get("role", "").strip() or "user"
        content = (item.get("content", "") or "").strip()
        if not content:
            continue
        lines.append(f"[{role}] {content}")
    return "\n".join(lines)


def insert_trace_section(report_text: str, trace_md: str) -> str:
    text = (report_text or "").strip()
    trace = (trace_md or "").strip()
    if not text:
        return trace
    if not trace:
        return text
    if "## 評估方式與引用檔案" in text:
        return text
    lines = text.splitlines()
    heading_indexes = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if len(heading_indexes) >= 2:
        insert_at = heading_indexes[1]
        new_lines = lines[:insert_at] + ["", trace, ""] + lines[insert_at:]
        return "\n".join(new_lines).strip()
    return f"{text}\n\n{trace}".strip()


def default_agents() -> list[dict[str, str]]:
    return [
        {
            "id": "integration-advisor",
            "name": "整合評估顧問（預設）",
            "role": "整合評估顧問",
            "goal": "根據整合評估報告回答問題，並給出具體、可執行的下一步建議。",
            "backstory": (
                "你擅長把技術報告轉成可落地的工作清單，"
                "會清楚區分已知事實、假設與需要補件的資訊。"
            ),
            "model": "",
        }
    ]


def load_agent_configs() -> list[dict[str, str]]:
    if not AGENTS_FILE.exists():
        data = default_agents()
        save_agent_configs(data)
        return data
    try:
        raw = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return default_agents()
        return [item for item in raw if isinstance(item, dict)]
    except Exception:
        return default_agents()


def save_agent_configs(items: list[dict[str, str]]) -> None:
    AGENTS_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def find_agent_config(agent_id: str | None) -> dict[str, str]:
    agents = load_agent_configs()
    if not agent_id:
        return agents[0] if agents else default_agents()[0]
    for item in agents:
        if item.get("id") == agent_id:
            return item
    raise HTTPException(status_code=404, detail=f"找不到 agent：{agent_id}")


def markdown_to_docx_bytes(md: str, base_dir: Path) -> bytes:
    try:
        import pypandoc
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail="伺服器未安裝 pypandoc，無法匯出 Word",
        ) from e
    text = (md or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="內容為空")
    tmpdir = Path(tempfile.mkdtemp(prefix="docx-"))
    out_path = tmpdir / "report.docx"
    ref_path = ensure_word_reference_docx(base_dir)
    extra_args: list[str] = [
        "--standalone",
        "-f",
        "markdown+smart",
        "-V",
        "lang=zh-TW",
    ]
    if ref_path is not None:
        extra_args.extend(["--reference-doc", str(ref_path)])
    try:
        pypandoc.convert_text(
            text,
            "docx",
            format="md",
            outputfile=str(out_path),
            extra_args=extra_args,
        )
    except RuntimeError as e:
        err = str(e).lower()
        if "pandoc" in err or "not found" in err:
            raise HTTPException(
                status_code=503,
                detail=(
                    "找不到 Pandoc 執行檔。Docker 映像已內建 pandoc；"
                    "本機開發請安裝：https://pandoc.org/installing.html"
                ),
            ) from e
        raise HTTPException(status_code=500, detail=f"匯出 Word 失敗：{e!s}") from e
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"匯出 Word 失敗：{e!s}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出 Word 失敗：{e!s}") from e
    try:
        return out_path.read_bytes()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def default_mount_paths() -> tuple[str, str]:
    return (
        os.getenv("MOUNT_PATH_A", "/projA").strip() or "/projA",
        os.getenv("MOUNT_PATH_B", "/projB").strip() or "/projB",
    )


def mount_roots_resolved() -> list[Path]:
    a, b = default_mount_paths()
    roots: list[Path] = []
    for p in (a, b):
        roots.append(Path(os.path.abspath(p)))
    return roots


def allowed_roots() -> list[Path]:
    roots = list(mount_roots_resolved())
    roots.append(UPLOAD_DIR.resolve())
    return roots


def path_is_under_allowed_roots(resolved: Path) -> bool:
    try:
        resolved = resolved.resolve()
    except OSError:
        return False
    for root in allowed_roots():
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def safe_extract_zip(zip_path: Path, dest: Path) -> None:
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            name = member.filename.replace("\\", "/")
            if name.startswith("/") or ".." in name.split("/"):
                raise HTTPException(status_code=400, detail="壓縮檔內含非法路徑")
            target = (dest / member.filename).resolve()
            try:
                target.relative_to(dest)
            except ValueError as e:
                raise HTTPException(status_code=400, detail="壓縮檔路徑不安全（zip slip）") from e
        zf.extractall(dest)


def detect_project_root(extract_dir: Path) -> Path:
    skip = {".DS_Store"}
    entries = [e for e in extract_dir.iterdir() if e.name not in skip and not e.name.startswith("__MACOSX")]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0].resolve()
    return extract_dir.resolve()


def display_git_url(url: str) -> str:
    p = urlparse(url)
    host = p.hostname or ""
    port = f":{p.port}" if p.port and p.scheme in ("http", "https") else ""
    path = p.path or ""
    q = f"?{p.query}" if p.query else ""
    return f"{p.scheme}://{host}{port}{path}{q}"


def validate_git_remote_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Git URL 不可為空")
    parsed = urlparse(raw)
    if parsed.scheme not in ("https", "http"):
        raise HTTPException(
            status_code=400,
            detail="目前僅支援 http(s) 遠端 URL。SSH（git@…）請改為 https，或在 URL 內含 token（私有庫）。",
        )
    host = (parsed.hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise HTTPException(status_code=400, detail="不允許 clone 到 localhost")
    if not host:
        raise HTTPException(status_code=400, detail="無效的 Git URL")
    return raw


def run_git_clone(url: str, dest: Path, branch: str | None) -> None:
    if shutil.which("git") is None:
        raise HTTPException(status_code=500, detail="伺服器未安裝 git，無法 clone")
    depth = max(1, int(os.getenv("GIT_CLONE_DEPTH", "1")))
    timeout = max(30, int(os.getenv("GIT_CLONE_TIMEOUT_SEC", "600")))
    cmd = ["git", "clone", "--depth", str(depth)]
    if branch and branch.strip():
        cmd.extend(["--branch", branch.strip()])
    cmd.extend([url, str(dest)])
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as e:
        raise HTTPException(
            status_code=504,
            detail=f"git clone 逾時（{timeout}s），可設定 GIT_CLONE_TIMEOUT_SEC",
        ) from e
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"無法執行 git：{e!s}") from e
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise HTTPException(status_code=400, detail=f"git clone 失敗：{err[:2500]}")


def resolve_and_validate_dir(path_value: str, label: str) -> str:
    raw = path_value.strip()
    if os.name != "nt" and re.match(r"^[A-Za-z]:\\", raw):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{label} 看起來是 Windows 路徑：{raw}\n"
                "目前服務在 Docker 容器內執行，請先用 -v 掛載後填「容器內路徑」，例如 /projA、/projB。"
            ),
        )
    resolved = os.path.abspath(os.path.expanduser(raw))
    if not os.path.isdir(resolved):
        mount_a, mount_b = default_mount_paths()
        hint = ""
        if resolved in {
            os.path.abspath(mount_a),
            os.path.abspath(mount_b),
        }:
            hint = (
                " 常見原因：Docker 未掛載該路徑。"
                "請在 `docker run` 加上 `-v \"你的專案資料夾:{mount_a}\"`（專案 B 同理用 `{mount_b}`）。"
            ).format(mount_a=mount_a, mount_b=mount_b)
        raise HTTPException(
            status_code=400,
            detail=f"{label} 不是有效目錄：{resolved}{hint}",
        )
    p = Path(resolved).resolve()
    if not path_is_under_allowed_roots(p):
        raise HTTPException(
            status_code=403,
            detail=(
                f"{label} 必須在允許範圍內："
                "Docker 掛載目錄（如 /projA）或「上傳 ZIP」產生的路徑（通常位於 uploads 下）。"
            ),
        )
    return str(p)


def run_chat_crew(
    user_message: str,
    report_text: str,
    history_text: str,
    agent_id: str | None,
) -> str:
    from crewai import Agent, Crew, LLM, Process, Task

    cfg = find_agent_config(agent_id)
    model_override = (cfg.get("model") or "").strip()
    llm = LLM(model=model_override) if model_override else build_llm()
    discuss_agent = Agent(
        role=cfg.get("role", "整合評估顧問"),
        goal=cfg.get("goal", "根據整合評估報告回答問題，並給出具體、可執行的下一步建議。"),
        backstory=cfg.get("backstory", "你是務實且清楚的顧問。"),
        llm=llm,
        verbose=False,
    )
    task = Task(
        description=(
            "你正在與使用者討論整合評估報告。\n"
            "請遵守：\n"
            "1) 先直接回答使用者問題。\n"
            "2) 若資訊不足，列出缺少的關鍵資訊。\n"
            "3) 最後提供 3-5 個可執行下一步。\n\n"
            f"目前使用的 Agent：{cfg.get('name', cfg.get('id', 'unknown'))}\n\n"
            f"報告內容（截斷）：\n{report_text}\n\n"
            f"近期對話（截斷）：\n{history_text}\n\n"
            f"使用者問題：\n{user_message}\n"
        ),
        expected_output="以繁體中文回覆，條列清楚、可執行。",
        agent=discuss_agent,
    )
    result = Crew(
        agents=[discuss_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    ).kickoff()
    return str(result)


def _extract_first_json_object(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass

    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return {}
    block = m.group(0)
    try:
        parsed = json.loads(block)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _normalize_option_item(item: dict, idx: int) -> dict:
    oid = str(item.get("id") or f"opt-{idx}")
    steps = item.get("steps") or []
    if not isinstance(steps, list):
        steps = [str(steps)]
    depends = item.get("depends_on") or []
    if not isinstance(depends, list):
        depends = [str(depends)]
    ac = item.get("acceptance_criteria") or []
    if not isinstance(ac, list):
        ac = [str(ac)]
    return {
        "id": oid,
        "title": str(item.get("title") or f"選項 {idx}"),
        "why": str(item.get("why") or ""),
        "steps": [str(x) for x in steps if str(x).strip()],
        "cost": str(item.get("cost") or "M"),
        "impact": str(item.get("impact") or "中"),
        "risk": str(item.get("risk") or ""),
        "depends_on": [str(x) for x in depends if str(x).strip()],
        "acceptance_criteria": [str(x) for x in ac if str(x).strip()],
    }


def generate_decision_options(
    report_text: str,
    prompt: str,
    max_options: int,
    agent_id: str | None,
) -> tuple[list[dict], str]:
    from crewai import Agent, Crew, LLM, Process, Task

    cfg = find_agent_config(agent_id)
    model_override = (cfg.get("model") or "").strip()
    llm = LLM(model=model_override) if model_override else build_llm()
    agent = Agent(
        role=cfg.get("role", "整合評估顧問"),
        goal="產生可比較且可執行的整合方案選項，避免空泛建議。",
        backstory=cfg.get("backstory", "你是務實且清楚的顧問。"),
        llm=llm,
        verbose=False,
    )
    task = Task(
        description=(
            "請根據報告與使用者需求，產出可比較的決策選項。\n"
            f"請輸出純 JSON 物件，格式：{{\"options\": [ ... ]}}。\n"
            "每個 option 欄位：id, title, why, steps, cost, impact, risk, depends_on, acceptance_criteria。\n"
            f"最多 {max_options} 個選項，請使用繁體中文。\n\n"
            f"使用者補充：{prompt or '（無）'}\n\n"
            f"報告內容（截斷）：\n{(report_text or '')[:18000]}"
        ),
        expected_output="純 JSON 字串，且包含 options 陣列。",
        agent=agent,
    )
    raw = str(Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff())
    parsed = _extract_first_json_object(raw)
    items = parsed.get("options") if isinstance(parsed, dict) else None
    if not isinstance(items, list):
        items = []
    normalized = [_normalize_option_item(x if isinstance(x, dict) else {}, i + 1) for i, x in enumerate(items)]
    if not normalized:
        normalized = [
            {
                "id": "opt-1",
                "title": "先建立最小可行整合計畫（2 週）",
                "why": "先降低不確定性，快速驗證可行性。",
                "steps": ["盤點高風險整合點", "建立 PoC", "定義里程碑與驗收"],
                "cost": "M",
                "impact": "高",
                "risk": "需求邊界可能變動",
                "depends_on": [],
                "acceptance_criteria": ["完成 PoC", "核心流程可跑通"],
            }
        ]
    return normalized[: max(1, max_options)], raw


def synthesize_selected_options(
    report_text: str,
    prompt: str,
    options: list[dict],
    selected_ids: list[str],
    ranked_ids: list[str],
    agent_id: str | None,
) -> str:
    from crewai import Agent, Crew, LLM, Process, Task

    cfg = find_agent_config(agent_id)
    model_override = (cfg.get("model") or "").strip()
    llm = LLM(model=model_override) if model_override else build_llm()
    agent = Agent(
        role=cfg.get("role", "整合評估顧問"),
        goal="將使用者選擇的方案整合為可執行建議與排程。",
        backstory=cfg.get("backstory", "你是務實且清楚的顧問。"),
        llm=llm,
        verbose=False,
    )
    selected = [x for x in options if x.get("id") in set(selected_ids)]
    if not selected:
        selected = options[:2]
    task = Task(
        description=(
            "請將以下選項整合成一份可落地建議，使用繁體中文 markdown，格式包含：\n"
            "1) 建議採用組合\n2) 1-2 週排程\n3) 風險與備援\n4) 立即下一步（3-5 點）\n\n"
            f"使用者補充：{prompt or '（無）'}\n"
            f"使用者選取 ID：{selected_ids}\n"
            f"使用者排序 ID：{ranked_ids}\n"
            f"候選選項(JSON)：{json.dumps(selected, ensure_ascii=False)}\n\n"
            f"報告內容（截斷）：\n{(report_text or '')[:16000]}"
        ),
        expected_output="繁體中文 markdown，條列清楚可執行。",
        agent=agent,
    )
    return str(Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff())


def patch_report_with_suggestion(
    report_id: str,
    suggestion_markdown: str,
    mode: str = "append",
    section_title: str = "決策與行動計畫",
) -> dict:
    if "/" in report_id or "\\" in report_id or ".." in report_id:
        raise HTTPException(status_code=400, detail="無效的 report_id")
    source = REPORTS_DIR / report_id
    if not source.is_file():
        raise HTTPException(status_code=404, detail="找不到報告")
    original = source.read_text(encoding="utf-8")
    suggestion = (suggestion_markdown or "").strip()
    if not suggestion:
        raise HTTPException(status_code=400, detail="suggestion_markdown 不可為空")

    if mode == "rewrite":
        patched = suggestion
    else:
        patched = f"{original.rstrip()}\n\n## {section_title}\n\n{suggestion}\n"

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = source.stem
    new_name = f"{ts}__{base}__patched.md"
    target = REPORTS_DIR / new_name
    target.write_text(patched, encoding="utf-8")
    return {
        "new_report_id": new_name,
        "mode": mode,
        "section_title": section_title,
    }


def run_assessment(project_a: str, project_b: str) -> tuple[str, str]:
    from integrapilot.crew import (
        build_evaluation_trace_markdown,
        create_integration_assessment_crew,
    )

    crew = create_integration_assessment_crew(project_a, project_b)
    result = crew.kickoff()
    raw_report = str(result)
    trace_md = build_evaluation_trace_markdown(project_a, project_b)
    result_text = insert_trace_section(raw_report, trace_md)
    report_id = save_report(project_a, project_b, result_text)
    return result_text, report_id


async def save_upload_zip_chunks(
    file: UploadFile,
    zip_path: Path,
    max_bytes: int,
) -> int:
    total = 0
    with open(zip_path, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                max_mb = max(1, max_bytes // (1024 * 1024))
                raise HTTPException(
                    status_code=413,
                    detail=f"檔案超過上限 {max_mb} MB（可用環境變數 MAX_UPLOAD_ZIP_MB 調整）",
                )
            out.write(chunk)
    return total


def list_directory_impl(path_query: str) -> dict:
    raw = path_query.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="path 不可為空")
    if os.name != "nt" and re.match(r"^[A-Za-z]:\\", raw):
        raise HTTPException(
            status_code=400,
            detail="請填容器內路徑（例如 /projA），不要用 C:\\...",
        )
    try:
        target = Path(raw).resolve()
    except OSError as e:
        raise HTTPException(status_code=400, detail=f"無效路徑：{e}") from e
    if not path_is_under_allowed_roots(target):
        roots = [str(p) for p in allowed_roots()]
        raise HTTPException(
            status_code=403,
            detail=f"僅能瀏覽允許範圍內的目錄。允許的根：{', '.join(roots)}",
        )
    if not target.is_dir():
        raise HTTPException(status_code=404, detail=f"不是目錄或不存在：{target}")
    entries: list[dict[str, str | bool]] = []
    try:
        names = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"無法讀取目錄：{e}") from e
    for p in names[:LIST_DIR_MAX_ENTRIES]:
        try:
            is_dir = p.is_dir()
        except OSError:
            continue
        entries.append(
            {
                "name": p.name,
                "path": str(p),
                "is_dir": is_dir,
            }
        )
    parent_path: str | None = None
    if target.parent != target:
        try:
            par = target.parent.resolve()
        except OSError:
            par = target.parent
        if path_is_under_allowed_roots(par):
            parent_path = str(par)
    return {
        "path": str(target),
        "parent": parent_path,
        "truncated": len(names) > LIST_DIR_MAX_ENTRIES,
        "entries": entries,
    }
