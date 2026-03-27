/** 工作台／評估 UI 共用型別（與後端 JSON 對齊） */

export type SectionId = "overview" | "assess" | "reports";

export interface MountProject {
  key: string;
  label: string;
  container_path: string;
  resolved_path: string;
  exists: boolean;
  host_hint: string;
}

export interface ReportItem {
  id: string;
  name: string;
  updated_at: string;
  size: number;
}

export interface BrowseEntry {
  name: string;
  path: string;
  is_dir: boolean;
}

export interface BrowseState {
  path: string;
  parent: string | null;
  entries: BrowseEntry[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AgentItem {
  id: string;
  name: string;
  role?: string;
  goal?: string;
  backstory?: string;
  model?: string;
}

export interface NewAgentForm {
  name: string;
  role: string;
  goal: string;
  backstory: string;
  model: string;
}

export interface DecisionOption {
  id: string;
  title: string;
  why: string;
  steps: string[];
  cost: string;
  impact: string;
  risk: string;
  depends_on: string[];
  acceptance_criteria: string[];
}

/** Element Plus el-upload 自訂 http-request 選項（精簡） */
export interface ZipUploadOptions {
  file: File | Blob;
  onSuccess?: (data: unknown) => void;
  onError?: (err: unknown) => void;
}
