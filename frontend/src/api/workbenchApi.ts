import {
  agentsResponseSchema,
  assessResponseSchema,
  browseStateSchema,
  chatResponseSchema,
  cloneRepoSchema,
  createAgentSchema,
  mountsResponseSchema,
  optionsGenerateSchema,
  optionsSynthesizeSchema,
  patchReportSchema,
  reportContentSchema,
  reportsListSchema,
  uploadZipSchema,
} from "@/api/schemas";
import { parseApi } from "@/api/parse";
import { detailMessage, fetchJson, postFormData } from "@/utils/api";
import type {
  AgentItem,
  BrowseState,
  ChatMessage,
  DecisionOption,
  MountProject,
  NewAgentForm,
  ReportItem,
} from "@/types/workbench";

export async function apiGetMounts(): Promise<{ projects: MountProject[]; hint: string }> {
  const { res, data } = await fetchJson("/api/mounts");
  if (!res.ok) throw new Error(detailMessage(data));
  return parseApi(mountsResponseSchema, data);
}

export async function apiGetReports(): Promise<ReportItem[]> {
  const { res, data } = await fetchJson("/api/reports");
  if (!res.ok) throw new Error(detailMessage(data));
  const parsed = parseApi(reportsListSchema, data);
  return parsed.reports;
}

export async function apiGetReportContent(id: string): Promise<{ id: string; content: string }> {
  const { res, data } = await fetchJson(`/api/reports/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(detailMessage(data));
  return parseApi(reportContentSchema, data);
}

export async function apiGetAgents(): Promise<AgentItem[]> {
  const { res, data } = await fetchJson("/api/agents");
  if (!res.ok) throw new Error(detailMessage(data));
  const parsed = parseApi(agentsResponseSchema, data);
  return parsed.agents;
}

export async function apiGetBrowse(path: string): Promise<BrowseState> {
  const { res, data } = await fetchJson(`/api/list?path=${encodeURIComponent(path)}`);
  if (!res.ok) throw new Error(detailMessage(data));
  return parseApi(browseStateSchema, data);
}

export async function apiAssess(projectA: string, projectB: string): Promise<{ result: string; report_id: string }> {
  const { res, data } = await fetchJson("/api/assess", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_a: projectA, project_b: projectB }),
  });
  if (!res.ok) throw new Error(detailMessage(data));
  return parseApi(assessResponseSchema, data);
}

export async function apiChat(body: {
  message: string;
  report_id: string | null;
  history: ChatMessage[];
  agent_id: string | null;
}): Promise<{ reply: string }> {
  const { res, data } = await fetchJson("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(detailMessage(data));
  return parseApi(chatResponseSchema, data);
}

export async function apiGenerateOptions(body: {
  report_id: string | null;
  prompt: string;
  max_options: number;
  agent_id: string | null;
}): Promise<{ options: DecisionOption[] }> {
  const { res, data } = await fetchJson("/api/options/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(detailMessage(data));
  return parseApi(optionsGenerateSchema, data);
}

export async function apiSynthesizeOptions(body: Record<string, unknown>): Promise<{ suggestion_markdown: string }> {
  const { res, data } = await fetchJson("/api/options/synthesize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(detailMessage(data));
  return parseApi(optionsSynthesizeSchema, data);
}

export async function apiPatchReport(
  reportId: string,
  body: { report_id: string; suggestion_markdown: string; mode: string; section_title: string },
): Promise<{ new_report_id?: string }> {
  const { res, data } = await fetchJson(`/api/reports/${encodeURIComponent(reportId)}/patch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(detailMessage(data));
  return parseApi(patchReportSchema, data);
}

export async function apiCreateAgent(payload: NewAgentForm): Promise<{ agentId?: string }> {
  const { res, data } = await fetchJson("/api/agents", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(detailMessage(data));
  const parsed = parseApi(createAgentSchema, data);
  return { agentId: parsed.agent?.id };
}

export async function apiDeleteAgent(agentId: string): Promise<void> {
  const { res, data } = await fetchJson(`/api/agents/${encodeURIComponent(agentId)}`, { method: "DELETE" });
  if (!res.ok) throw new Error(detailMessage(data));
}

export async function apiCloneRepo(slot: "a" | "b", url: string, branch: string | null): Promise<string> {
  const { res, data } = await fetchJson("/api/clone-repo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slot, url, branch }),
  });
  if (!res.ok) throw new Error(detailMessage(data));
  const parsed = parseApi(cloneRepoSchema, data);
  return parsed.path;
}

export async function apiUploadZip(slot: "a" | "b", file: File): Promise<string> {
  const fd = new FormData();
  fd.append("slot", slot);
  fd.append("file", file);
  const { res, data } = await postFormData("/api/upload-zip", fd);
  if (!res.ok) throw new Error(detailMessage(data));
  const parsed = parseApi(uploadZipSchema, data);
  return parsed.path;
}
