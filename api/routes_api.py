"""REST API：/api/* 路由。"""

import os
import shutil
import zipfile
from uuid import uuid4

from fastapi import APIRouter, Body, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from api import db
from api import helpers as h
from api.config import BASE_DIR, REPORTS_DIR, UPLOAD_DIR
from api.helpers import save_upload_zip_chunks
from api.limiter_ext import rate_limit
from api.schemas import (
    AgentCreateRequest,
    AssessRequest,
    ChatRequest,
    CloneRepoRequest,
    GenerateOptionsRequest,
    ExportDocxRequest,
    PatchReportRequest,
    SynthesizeOptionsRequest,
)

router = APIRouter(prefix="/api")


@router.get("/mounts")
def get_mounts() -> dict:
    path_a, path_b = h.default_mount_paths()
    abs_a = os.path.abspath(path_a)
    abs_b = os.path.abspath(path_b)

    def _proj(key: str, label: str, container_path: str, abs_path: str) -> dict:
        hint = os.getenv(f"MOUNT_HOST_HINT_{key}", "").strip()
        exists = os.path.isdir(abs_path)
        return {
            "key": key,
            "label": label,
            "container_path": container_path,
            "resolved_path": abs_path,
            "exists": exists,
            "host_hint": hint,
        }

    return {
        "projects": [
            _proj("A", "專案 A", path_a, abs_a),
            _proj("B", "專案 B", path_b, abs_b),
        ],
        "hint": (
            "方式一：在「建立評估」上傳 ZIP 或貼上 Git https URL 執行 clone，系統會自動填入路徑（通常不需 docker -v）。"
            "方式二：在輸入框填「容器內路徑」（上表 resolved_path）；"
            "若用 docker -v 掛載，通常為 /projA 與 /projB。"
        ),
    }


@router.get("/reports")
def list_reports() -> dict:
    rows = db.list_reports()
    if not rows:
        files = sorted(REPORTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        items = [
            {
                "id": p.name,
                "name": p.name,
                "updated_at": h.timestamp_to_taipei_iso(p.stat().st_mtime),
                "size": p.stat().st_size,
            }
            for p in files
        ]
        return {"reports": items}

    items = []
    for r in rows:
        updated_at = r["updated_at"]
        items.append(
            {
                "id": r["id"],
                "name": r["name"],
                "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at),
                "size": r["size"],
            }
        )
    return {"reports": items}


@router.get("/reports/{report_id}")
def get_report(report_id: str) -> dict[str, str]:
    if "/" in report_id or "\\" in report_id or ".." in report_id:
        raise HTTPException(status_code=400, detail="無效的 report_id")
    target = REPORTS_DIR / report_id
    if not target.is_file():
        raise HTTPException(status_code=404, detail="找不到報告")
    return {"id": report_id, "content": target.read_text(encoding="utf-8")}


@router.post("/export-docx")
def export_docx(payload: ExportDocxRequest) -> Response:
    data = h.markdown_to_docx_bytes(payload.markdown, BASE_DIR)
    ts = h.now_taipei().strftime("%Y%m%d-%H%M%S")
    filename = f"integration-report-{ts}.docx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/upload-zip")
async def upload_zip(
    slot: str = Form(..., description="a 或 b"),
    file: UploadFile = File(..., description="專案 ZIP"),
) -> dict:
    s = (slot or "").strip().lower()
    if s not in ("a", "b"):
        raise HTTPException(status_code=400, detail="slot 必須為 a 或 b")

    filename = (file.filename or "project.zip").strip()
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="請上傳副檔名為 .zip 的檔案")

    max_mb = int(os.getenv("MAX_UPLOAD_ZIP_MB", "80"))
    max_bytes = max(1, max_mb) * 1024 * 1024

    job_id = uuid4().hex
    work = UPLOAD_DIR / job_id
    work.mkdir(parents=True, exist_ok=True)
    zip_path = work / "upload.zip"

    try:
        total = await save_upload_zip_chunks(file, zip_path, max_bytes)
    except HTTPException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(work, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"儲存上傳失敗：{e!s}") from e

    extract_dir = work / "extract"
    try:
        h.safe_extract_zip(zip_path, extract_dir)
    except HTTPException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    except zipfile.BadZipFile as e:
        shutil.rmtree(work, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"不是有效的 ZIP：{e!s}") from e

    root = h.detect_project_root(extract_dir)
    if not root.is_dir():
        shutil.rmtree(work, ignore_errors=True)
        raise HTTPException(status_code=400, detail="解壓後找不到有效專案目錄")

    out = {
        "slot": s,
        "path": str(root),
        "upload_id": job_id,
        "zip_name": filename,
        "bytes": total,
    }
    db.create_input_asset(
        slot=s,
        source_type="zip",
        resolved_path=out["path"],
        now=h.now_taipei(),
        upload_id=job_id,
        origin_url=None,
        branch=None,
        size_bytes=total,
    )
    return out


@router.post("/clone-repo")
def clone_repo(payload: CloneRepoRequest) -> dict:
    s = (payload.slot or "").strip().lower()
    if s not in ("a", "b"):
        raise HTTPException(status_code=400, detail="slot 必須為 a 或 b")
    url = h.validate_git_remote_url(payload.url)

    job_id = uuid4().hex
    work = UPLOAD_DIR / job_id
    repo_dir = work / "repo"
    try:
        work.mkdir(parents=True, exist_ok=True)
        h.run_git_clone(url, repo_dir, payload.branch)
    except HTTPException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(work, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"clone 失敗：{e!s}") from e

    if not repo_dir.is_dir():
        shutil.rmtree(work, ignore_errors=True)
        raise HTTPException(status_code=400, detail="clone 後目錄不存在")

    out = {
        "slot": s,
        "path": str(repo_dir.resolve()),
        "upload_id": job_id,
        "url": h.display_git_url(url),
    }
    db.create_input_asset(
        slot=s,
        source_type="clone",
        resolved_path=out["path"],
        now=h.now_taipei(),
        upload_id=job_id,
        origin_url=out["url"],
        branch=payload.branch,
        size_bytes=None,
    )
    return out


@router.get("/agents")
def list_agents() -> dict:
    return {"agents": h.load_agent_configs()}


@router.post("/agents")
def create_agent(payload: AgentCreateRequest) -> dict:
    name = payload.name.strip()
    role = payload.role.strip()
    goal = payload.goal.strip()
    backstory = payload.backstory.strip()
    model = (payload.model or "").strip()
    if not name or not role or not goal or not backstory:
        raise HTTPException(status_code=400, detail="name/role/goal/backstory 不可為空")

    item = db.create_agent(name, role, goal, backstory, model, h.now_taipei())
    return {"agent": item}


@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: str) -> dict:
    if agent_id == "integration-advisor":
        raise HTTPException(status_code=400, detail="預設 agent 不可刪除")
    ok = db.deactivate_agent(agent_id, h.now_taipei())
    if not ok:
        raise HTTPException(status_code=404, detail="找不到要刪除的 agent")
    return {"ok": True}


@router.post("/chat")
@rate_limit(os.getenv("RATE_LIMIT_CHAT", "30/minute"))
def chat_about_report(request: Request, payload: ChatRequest = Body(...)) -> dict[str, str]:
    if not os.getenv("GOOGLE_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="未設定 GOOGLE_API_KEY，請先在 .env 設定。",
        )

    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="message 不可為空")

    report_text = h.load_report_text(payload.report_id)[:20000]
    history_text = h.history_to_text(payload.history, max_turns=8)

    reply = h.run_chat_crew(
        user_message=user_message,
        report_text=report_text,
        history_text=history_text,
        agent_id=payload.agent_id,
    )
    return {"reply": reply}


@router.get("/list")
def list_directory(
    path: str = Query(..., description="要列出的目錄（須為允許的掛載根之下）"),
) -> dict:
    return h.list_directory_impl(path)


@router.post("/assess")
@rate_limit(os.getenv("RATE_LIMIT_ASSESS", "5/minute"))
def assess(request: Request, payload: AssessRequest = Body(...)) -> dict[str, str]:
    a = h.resolve_and_validate_input_path(payload.project_a, "專案 A")
    b = h.resolve_and_validate_input_path(payload.project_b, "專案 B")

    if not os.getenv("GOOGLE_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="未設定 GOOGLE_API_KEY，請先在 .env 設定。",
        )

    result_text, report_id = h.run_assessment(a, b)
    return {"result": result_text, "report_id": report_id}


@router.post("/options/generate")
@rate_limit(os.getenv("RATE_LIMIT_CHAT", "30/minute"))
def generate_options(request: Request, payload: dict = Body(...)) -> dict:
    payload_obj = GenerateOptionsRequest.model_validate(payload)
    if not os.getenv("GOOGLE_API_KEY"):
        raise HTTPException(status_code=500, detail="未設定 GOOGLE_API_KEY，請先在 .env 設定。")
    report_text = h.load_report_text(payload_obj.report_id)[:20000]
    options, raw_reply = h.generate_decision_options(
        report_text=report_text,
        prompt=(payload_obj.prompt or "").strip(),
        max_options=payload_obj.max_options,
        agent_id=payload_obj.agent_id,
    )
    return {"options": options, "raw_reply": raw_reply}


@router.post("/options/synthesize")
@rate_limit(os.getenv("RATE_LIMIT_CHAT", "30/minute"))
def synthesize_options(request: Request, payload: dict = Body(...)) -> dict:
    payload_obj = SynthesizeOptionsRequest.model_validate(payload)
    if not os.getenv("GOOGLE_API_KEY"):
        raise HTTPException(status_code=500, detail="未設定 GOOGLE_API_KEY，請先在 .env 設定。")
    report_text = h.load_report_text(payload_obj.report_id)[:20000]
    suggestion = h.synthesize_selected_options(
        report_text=report_text,
        prompt=(payload_obj.prompt or "").strip(),
        options=[x.model_dump() for x in payload_obj.options],
        selected_ids=payload_obj.selected_ids,
        ranked_ids=payload_obj.ranked_ids,
        agent_id=payload_obj.agent_id,
    )
    return {"suggestion_markdown": suggestion}


@router.post("/reports/{report_id}/patch")
def patch_report(report_id: str, payload: dict = Body(...)) -> dict:
    payload_obj = PatchReportRequest.model_validate(payload)
    if payload_obj.report_id != report_id:
        raise HTTPException(status_code=400, detail="路徑 report_id 與 body report_id 不一致")
    result = h.patch_report_with_suggestion(
        report_id=report_id,
        suggestion_markdown=payload_obj.suggestion_markdown,
        mode=payload_obj.mode,
        section_title=payload_obj.section_title,
    )
    return {"ok": True, **result}
