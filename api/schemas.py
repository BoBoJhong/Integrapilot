"""Pydantic 請求／回應模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AssessRequest(BaseModel):
    project_a: str = Field(..., description="專案 A 根目錄路徑")
    project_b: str = Field(..., description="專案 B 根目錄路徑")


class ChatRequest(BaseModel):
    message: str = Field(..., description="使用者訊息")
    report_id: str | None = Field(default=None, description="報告檔案名稱（可選）")
    history: list[dict[str, str]] = Field(default_factory=list, description="對話歷史")
    agent_id: str | None = Field(default=None, description="自訂 Agent ID（可選）")


class AgentConfig(BaseModel):
    id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="顯示名稱")
    role: str = Field(..., description="Agent 角色")
    goal: str = Field(..., description="Agent 目標")
    backstory: str = Field(..., description="Agent 背景敘述")
    model: str | None = Field(default=None, description="模型名稱（可選）")


class AgentCreateRequest(BaseModel):
    name: str = Field(..., description="顯示名稱")
    role: str = Field(..., description="Agent 角色")
    goal: str = Field(..., description="Agent 目標")
    backstory: str = Field(..., description="Agent 背景敘述")
    model: str | None = Field(default=None, description="模型名稱（可選）")


class CloneRepoRequest(BaseModel):
    slot: str = Field(..., description="a 或 b")
    url: str = Field(..., description="Git 遠端 URL（建議 https）")
    branch: str | None = Field(default=None, description="分支或 tag（可選）")


class ExportDocxRequest(BaseModel):
    markdown: str = Field(..., description="要匯出的 Markdown 全文")


class DecisionOption(BaseModel):
    id: str = Field(..., description="選項 ID")
    title: str = Field(..., description="選項標題")
    why: str = Field(..., description="為何建議此選項")
    steps: list[str] = Field(default_factory=list, description="執行步驟")
    cost: str = Field(default="M", description="成本（S/M/L）")
    impact: str = Field(default="中", description="影響（高/中/低）")
    risk: str = Field(default="", description="主要風險")
    depends_on: list[str] = Field(default_factory=list, description="相依項")
    acceptance_criteria: list[str] = Field(default_factory=list, description="驗收標準")


class GenerateOptionsRequest(BaseModel):
    report_id: str | None = Field(default=None, description="報告檔案名稱（可選）")
    prompt: str = Field(default="", description="使用者補充需求")
    max_options: int = Field(default=5, ge=2, le=8, description="最多產生選項數")
    agent_id: str | None = Field(default=None, description="指定 Agent（可選）")


class SynthesizeOptionsRequest(BaseModel):
    report_id: str | None = Field(default=None, description="報告檔案名稱（可選）")
    prompt: str = Field(default="", description="使用者補充限制")
    selected_ids: list[str] = Field(default_factory=list, description="使用者選取的選項 ID")
    ranked_ids: list[str] = Field(default_factory=list, description="使用者排序後的選項 ID（高優先在前）")
    options: list[DecisionOption] = Field(default_factory=list, description="完整選項清單")
    agent_id: str | None = Field(default=None, description="指定 Agent（可選）")


class PatchReportRequest(BaseModel):
    report_id: str = Field(..., description="原始報告 ID")
    suggestion_markdown: str = Field(..., description="綜合建議內容（Markdown）")
    mode: str = Field(default="append", description="append 或 rewrite（MVP 先支援 append）")
    section_title: str = Field(default="決策與行動計畫", description="要新增的章節標題")
