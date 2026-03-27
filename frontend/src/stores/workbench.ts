import { ElMessage } from "element-plus";
import { defineStore } from "pinia";
import { computed, nextTick, ref, watch, type Ref } from "vue";
import * as api from "@/api/workbenchApi";
import { queryKeys } from "@/api/queryKeys";
import { queryClient } from "@/queryClient";
import type {
  AgentItem,
  BrowseState,
  ChatMessage,
  DecisionOption,
  MountProject,
  NewAgentForm,
  ReportItem,
  SectionId,
  ZipUploadOptions,
} from "@/types/workbench";
import { sanitizeMd } from "@/utils/markdown";

export const useWorkbenchStore = defineStore("workbench", () => {
  const section = ref<SectionId>("overview");
  const projectA = ref(localStorage.getItem("projectA") || "");
  const projectB = ref(localStorage.getItem("projectB") || "");
  const loading = ref(false);
  const error = ref("");
  const result = ref("");
  const statusText = ref("準備就緒");
  const mounts = ref<MountProject[]>([]);
  const mountHint = ref("");
  const reports = ref<ReportItem[]>([]);
  const browseA = ref<BrowseState>({ path: "", parent: null, entries: [] });
  const browseB = ref<BrowseState>({ path: "", parent: null, entries: [] });
  const activeReportId = ref("");
  const reportTab = ref("preview");
  const chatInput = ref("");
  const chatLoading = ref(false);
  const chatMessages = ref<ChatMessage[]>([]);
  const chatLogEl: Ref<HTMLElement | null> = ref(null);
  const agents = ref<AgentItem[]>([]);
  const selectedAgentId = ref("integration-advisor");
  const showAgentForm = ref(false);
  const agentSaving = ref(false);
  const newAgent = ref<NewAgentForm>({
    name: "",
    role: "",
    goal: "",
    backstory: "",
    model: "",
  });
  const exportWordLoading = ref(false);
  const zipUploadA = ref(false);
  const zipUploadB = ref(false);
  const gitUrlA = ref("");
  const gitBranchA = ref("");
  const gitUrlB = ref("");
  const gitBranchB = ref("");
  const gitCloneA = ref(false);
  const gitCloneB = ref(false);
  const optionPrompt = ref("");
  const optionLoading = ref(false);
  const decisionOptions = ref<DecisionOption[]>([]);
  const selectedOptionIds = ref<string[]>([]);
  const rankedOptionIds = ref<string[]>([]);
  const suggestionLoading = ref(false);
  const suggestionMarkdown = ref("");
  const patchLoading = ref(false);

  const sectionTitle = computed(() => {
    const map: Record<SectionId, string> = {
      overview: "概覽",
      assess: "建立評估",
      reports: "報告與討論",
    };
    return map[section.value] || "";
  });

  const sectionDesc = computed(() => {
    const map: Record<SectionId, string> = {
      overview: "確認環境與建議使用方式",
      assess: "設定兩個專案路徑並產出整合報告",
      reports: "左側閱讀報告，右側以 Agent 對話追問與下一步",
    };
    return map[section.value] || "";
  });

  const renderedReport = computed(() => sanitizeMd(result.value));

  const selectedAgentLabel = computed(() => {
    const a = agents.value.find((x) => x.id === selectedAgentId.value);
    return a?.name || "整合顧問";
  });

  const selectedAgentInitial = computed(() => {
    const n = selectedAgentLabel.value.trim();
    return n ? n.slice(0, 1) : "A";
  });

  const statusType = computed(() => {
    if (statusText.value.includes("失敗")) return "danger";
    if (statusText.value.includes("完成") || statusText.value.includes("已")) return "success";
    if (statusText.value.includes("中") || statusText.value.includes("回覆")) return "warning";
    return "info";
  });

  watch(projectA, (v) => localStorage.setItem("projectA", v || ""));
  watch(projectB, (v) => localStorage.setItem("projectB", v || ""));
  watch(chatMessages, () => nextTick(() => scrollChatToBottom()));

  function scrollChatToBottom(): void {
    const el = chatLogEl.value;
    if (el) el.scrollTop = el.scrollHeight;
  }

  function onChatKeydown(e: Event | KeyboardEvent): void {
    if (!(e instanceof KeyboardEvent)) return;
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void sendChat();
    }
  }

  function fmtTime(iso: string): string {
    const d = new Date(iso || "");
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
  }

  function setStatus(t: string): void {
    statusText.value = t;
  }

  function clearResult(): void {
    result.value = "";
    error.value = "";
    activeReportId.value = "";
  }

  function clearChat(): void {
    chatMessages.value = [];
    chatInput.value = "";
    ElMessage.success("已清空對話");
  }

  function swapPaths(): void {
    const t = projectA.value;
    projectA.value = projectB.value;
    projectB.value = t;
  }

  async function cloneFromGit(slot: "a" | "b"): Promise<void> {
    const url = slot === "a" ? gitUrlA.value.trim() : gitUrlB.value.trim();
    const branchRaw = slot === "a" ? gitBranchA.value.trim() : gitBranchB.value.trim();
    if (!url) {
      ElMessage.warning("請貼上 Git https URL");
      return;
    }
    if (slot === "a") gitCloneA.value = true;
    else gitCloneB.value = true;
    error.value = "";
    try {
      const path = await api.apiCloneRepo(slot, url, branchRaw || null);
      if (slot === "a") projectA.value = path;
      else projectB.value = path;
      await loadList(slot, path);
      setStatus(`已 clone 專案 ${slot.toUpperCase()}`);
      ElMessage.success(`專案 ${slot.toUpperCase()} 已從 Git 就緒`);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      error.value = msg;
      ElMessage.error(msg);
    } finally {
      if (slot === "a") gitCloneA.value = false;
      else gitCloneB.value = false;
    }
  }

  async function onZipUpload(slot: "a" | "b", options: ZipUploadOptions): Promise<void> {
    const raw = options.file as File;
    if (!raw) return;
    if (slot === "a") zipUploadA.value = true;
    else zipUploadB.value = true;
    error.value = "";
    try {
      const path = await api.apiUploadZip(slot, raw);
      if (slot === "a") projectA.value = path;
      else projectB.value = path;
      await loadList(slot, path);
      setStatus(`已解壓專案 ${slot.toUpperCase()}`);
      ElMessage.success(`專案 ${slot.toUpperCase()} 已就緒`);
      options.onSuccess?.({ path });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      error.value = msg;
      ElMessage.error(msg);
      options.onError?.(e);
    } finally {
      if (slot === "a") zipUploadA.value = false;
      else zipUploadB.value = false;
    }
  }

  async function loadAll(): Promise<void> {
    error.value = "";
    setStatus("同步中…");
    try {
      const [m, r, a] = await Promise.all([
        queryClient.fetchQuery({
          queryKey: queryKeys.mounts,
          queryFn: () => api.apiGetMounts(),
        }),
        queryClient.fetchQuery({
          queryKey: queryKeys.reports,
          queryFn: () => api.apiGetReports(),
        }),
        queryClient.fetchQuery({
          queryKey: queryKeys.agents,
          queryFn: () => api.apiGetAgents(),
        }),
      ]);
      mounts.value = m.projects;
      mountHint.value = m.hint;
      reports.value = r;
      agents.value = a;
      if (!agents.value.some((x) => x.id === selectedAgentId.value)) {
        selectedAgentId.value = agents.value[0]?.id || "integration-advisor";
      }

      const ma = mounts.value.find((x) => x.key === "A");
      const mb = mounts.value.find((x) => x.key === "B");
      if (!projectA.value && ma?.resolved_path) projectA.value = ma.resolved_path;
      if (!projectB.value && mb?.resolved_path) projectB.value = mb.resolved_path;
      if (projectA.value) await loadList("a", projectA.value);
      if (projectB.value) await loadList("b", projectB.value);
      setStatus("已同步");
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e);
      setStatus("同步失敗");
    }
  }

  async function loadAgents(): Promise<void> {
    try {
      const list = await queryClient.fetchQuery({
        queryKey: queryKeys.agents,
        queryFn: () => api.apiGetAgents(),
      });
      agents.value = list;
      if (!agents.value.some((x) => x.id === selectedAgentId.value)) {
        selectedAgentId.value = agents.value[0]?.id || "integration-advisor";
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  async function createAgent(): Promise<void> {
    const payload = { ...newAgent.value };
    if (!payload.name || !payload.role || !payload.goal || !payload.backstory) {
      ElMessage.warning("請填完 Agent 名稱、角色、目標、背景");
      return;
    }
    agentSaving.value = true;
    try {
      const { agentId } = await api.apiCreateAgent(payload);
      await queryClient.invalidateQueries({ queryKey: queryKeys.agents });
      await loadAgents();
      if (agentId) selectedAgentId.value = agentId;
      showAgentForm.value = false;
      newAgent.value = { name: "", role: "", goal: "", backstory: "", model: "" };
      ElMessage.success("Agent 已建立");
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e);
      ElMessage.error(error.value);
    } finally {
      agentSaving.value = false;
    }
  }

  async function removeAgent(): Promise<void> {
    if (!selectedAgentId.value || selectedAgentId.value === "integration-advisor") return;
    try {
      await api.apiDeleteAgent(selectedAgentId.value);
      selectedAgentId.value = "integration-advisor";
      await queryClient.invalidateQueries({ queryKey: queryKeys.agents });
      await loadAgents();
      ElMessage.success("Agent 已刪除");
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e);
      ElMessage.error(error.value);
    }
  }

  async function loadMounts(): Promise<void> {
    try {
      const m = await api.apiGetMounts();
      mounts.value = m.projects;
      mountHint.value = m.hint;
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  async function loadReports(): Promise<void> {
    try {
      const list = await queryClient.fetchQuery({
        queryKey: queryKeys.reports,
        queryFn: () => api.apiGetReports(),
      });
      reports.value = list;
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  async function openReport(id: string): Promise<void> {
    try {
      setStatus("載入報告…");
      const data = await queryClient.fetchQuery({
        queryKey: queryKeys.report(id),
        queryFn: () => api.apiGetReportContent(id),
      });
      activeReportId.value = id;
      result.value = data.content || "";
      decisionOptions.value = [];
      selectedOptionIds.value = [];
      rankedOptionIds.value = [];
      suggestionMarkdown.value = "";
      reportTab.value = "preview";
      section.value = "reports";
      setStatus(`已載入：${id}`);
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  function toggleOptionSelected(id: string, checked: boolean): void {
    const set = new Set(selectedOptionIds.value);
    if (checked) set.add(id);
    else set.delete(id);
    selectedOptionIds.value = [...set];
  }

  function moveSelectedOption(id: string, dir: "up" | "down"): void {
    const arr = [...selectedOptionIds.value];
    const idx = arr.findIndex((x) => x === id);
    if (idx < 0) return;
    const swap = dir === "up" ? idx - 1 : idx + 1;
    if (swap < 0 || swap >= arr.length) return;
    const t = arr[idx];
    arr[idx] = arr[swap];
    arr[swap] = t;
    selectedOptionIds.value = arr;
  }

  async function generateOptions(): Promise<void> {
    if (!activeReportId.value && !result.value) {
      ElMessage.warning("請先載入或產生報告");
      return;
    }
    optionLoading.value = true;
    error.value = "";
    try {
      const data = await api.apiGenerateOptions({
        report_id: activeReportId.value || null,
        prompt: optionPrompt.value.trim(),
        max_options: 5,
        agent_id: selectedAgentId.value || null,
      });
      decisionOptions.value = data.options || [];
      selectedOptionIds.value = decisionOptions.value.map((x) => x.id);
      rankedOptionIds.value = [...selectedOptionIds.value];
      suggestionMarkdown.value = "";
      ElMessage.success("已產生方案選項");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      error.value = msg;
      ElMessage.error(msg);
    } finally {
      optionLoading.value = false;
    }
  }

  async function synthesizeOptions(): Promise<void> {
    if (!decisionOptions.value.length) {
      ElMessage.warning("請先產生方案選項");
      return;
    }
    suggestionLoading.value = true;
    error.value = "";
    try {
      const data = await api.apiSynthesizeOptions({
        report_id: activeReportId.value || null,
        prompt: optionPrompt.value.trim(),
        selected_ids: selectedOptionIds.value,
        ranked_ids: selectedOptionIds.value,
        options: decisionOptions.value,
        agent_id: selectedAgentId.value || null,
      });
      suggestionMarkdown.value = data.suggestion_markdown || "";
      ElMessage.success("已產生綜合建議");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      error.value = msg;
      ElMessage.error(msg);
    } finally {
      suggestionLoading.value = false;
    }
  }

  async function patchReportBySuggestion(): Promise<void> {
    if (!activeReportId.value) {
      ElMessage.warning("請先選擇報告");
      return;
    }
    if (!suggestionMarkdown.value.trim()) {
      ElMessage.warning("請先產生綜合建議");
      return;
    }
    patchLoading.value = true;
    error.value = "";
    try {
      const reportId = activeReportId.value;
      const data = await api.apiPatchReport(reportId, {
        report_id: reportId,
        suggestion_markdown: suggestionMarkdown.value,
        mode: "append",
        section_title: "決策與行動計畫",
      });
      const newId = data.new_report_id;
      await queryClient.invalidateQueries({ queryKey: queryKeys.reports });
      await loadReports();
      if (newId) await openReport(newId);
      ElMessage.success("已套用建議並建立新報告版本");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      error.value = msg;
      ElMessage.error(msg);
    } finally {
      patchLoading.value = false;
    }
  }

  async function loadList(which: "a" | "b", path: string): Promise<void> {
    if (!path) return;
    try {
      const data = await api.apiGetBrowse(path);
      if (which === "a") browseA.value = data;
      else browseB.value = data;
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  function applyPath(key: string, path: string): void {
    if (key === "A") {
      projectA.value = path;
      void loadList("a", path);
    }
    if (key === "B") {
      projectB.value = path;
      void loadList("b", path);
    }
    ElMessage.success("已套用路徑");
  }

  function copy(text: string): void {
    void navigator.clipboard.writeText(text || "").then(() => {
      setStatus("已複製");
      ElMessage.success("內容已複製到剪貼簿");
    });
  }

  function downloadResult(): void {
    if (!result.value) return;
    const blob = new Blob([result.value], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${new Date().toISOString().replace(/[:.]/g, "-")}.md`;
    a.click();
    URL.revokeObjectURL(url);
    setStatus("已下載");
    ElMessage.success("報告已下載");
  }

  async function downloadWord(): Promise<void> {
    if (!result.value) return;
    exportWordLoading.value = true;
    error.value = "";
    try {
      const res = await fetch("/api/export-docx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ markdown: result.value }),
      });
      if (!res.ok) {
        const text = await res.text();
        let detail = "匯出失敗";
        try {
          const j = JSON.parse(text) as { detail?: unknown };
          const d = j.detail;
          detail = typeof d === "string" ? d : JSON.stringify(d);
        } catch {
          detail = text.slice(0, 300);
        }
        throw new Error(detail);
      }
      const blob = await res.blob();
      const cd = res.headers.get("Content-Disposition");
      let name = `integration-report-${new Date().toISOString().replace(/[:.]/g, "-")}.docx`;
      if (cd) {
        const m = /filename="([^"]+)"/.exec(cd);
        if (m) name = m[1];
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);
      setStatus("已匯出 Word");
      ElMessage.success("Word 已下載（由 Markdown 轉成標題與段落樣式）");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      error.value = msg;
      ElMessage.error(msg);
    } finally {
      exportWordLoading.value = false;
    }
  }

  async function submitForm(): Promise<void> {
    error.value = "";
    result.value = "";
    if (!projectA.value || !projectB.value) {
      error.value = "請填寫專案 A 與 B 路徑";
      ElMessage.warning("請先填寫兩個專案路徑");
      return;
    }
    loading.value = true;
    setStatus("評估進行中（約 1–3 分鐘）…");
    try {
      const data = await api.apiAssess(projectA.value, projectB.value);
      result.value = data.result || "";
      activeReportId.value = data.report_id || "";
      await queryClient.invalidateQueries({ queryKey: queryKeys.reports });
      if (data.report_id) {
        await queryClient.invalidateQueries({ queryKey: queryKeys.report(data.report_id) });
      }
      await loadReports();
      reportTab.value = "preview";
      section.value = "reports";
      setStatus("評估完成");
      ElMessage.success("整合評估完成");
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e);
      setStatus("評估失敗");
      ElMessage.error(error.value);
    } finally {
      loading.value = false;
    }
  }

  async function sendChat(): Promise<void> {
    const msg = (chatInput.value || "").trim();
    if (!msg) return;
    if (!activeReportId.value && !result.value) {
      error.value = "請先載入或產生報告";
      section.value = "reports";
      ElMessage.warning("請先載入或產生報告");
      return;
    }
    chatMessages.value.push({ role: "user", content: msg });
    chatInput.value = "";
    chatLoading.value = true;
    setStatus("Agent 回覆中…");
    try {
      const data = await api.apiChat({
        message: msg,
        report_id: activeReportId.value || null,
        history: chatMessages.value.slice(-10),
        agent_id: selectedAgentId.value || null,
      });
      chatMessages.value.push({ role: "assistant", content: data.reply || "" });
      setStatus("已回覆");
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e);
      setStatus("對話失敗");
      ElMessage.error(error.value);
    } finally {
      chatLoading.value = false;
    }
  }

  return {
    section,
    projectA,
    projectB,
    loading,
    error,
    result,
    statusText,
    mounts,
    mountHint,
    reports,
    browseA,
    browseB,
    activeReportId,
    reportTab,
    chatInput,
    chatLoading,
    chatMessages,
    chatLogEl,
    agents,
    selectedAgentId,
    showAgentForm,
    agentSaving,
    newAgent,
    exportWordLoading,
    zipUploadA,
    zipUploadB,
    gitUrlA,
    gitBranchA,
    gitUrlB,
    gitBranchB,
    gitCloneA,
    gitCloneB,
    optionPrompt,
    optionLoading,
    decisionOptions,
    selectedOptionIds,
    rankedOptionIds,
    suggestionLoading,
    suggestionMarkdown,
    patchLoading,
    sectionTitle,
    sectionDesc,
    renderedReport,
    selectedAgentLabel,
    selectedAgentInitial,
    statusType,
    scrollChatToBottom,
    onChatKeydown,
    fmtTime,
    setStatus,
    clearResult,
    clearChat,
    swapPaths,
    cloneFromGit,
    onZipUpload,
    loadAll,
    loadAgents,
    createAgent,
    removeAgent,
    loadMounts,
    loadReports,
    openReport,
    toggleOptionSelected,
    moveSelectedOption,
    generateOptions,
    synthesizeOptions,
    patchReportBySuggestion,
    loadList,
    applyPath,
    copy,
    downloadResult,
    downloadWord,
    submitForm,
    sendChat,
  };
});
