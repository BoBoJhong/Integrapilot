import { z } from "zod";

const mountProject = z.object({
  key: z.string(),
  label: z.string(),
  container_path: z.string(),
  resolved_path: z.string(),
  exists: z.boolean(),
  host_hint: z.string(),
});

export const mountsResponseSchema = z.object({
  projects: z.array(mountProject).default([]),
  hint: z.string().optional().default(""),
});

export const reportItemSchema = z.object({
  id: z.string(),
  name: z.string(),
  updated_at: z.string(),
  size: z.number(),
});

export const reportsListSchema = z.object({
  reports: z.array(reportItemSchema).default([]),
});

export const reportContentSchema = z.object({
  id: z.string(),
  content: z.string(),
});

export const agentItemSchema = z.object({
  id: z.string(),
  name: z.string(),
  role: z.string().optional(),
  goal: z.string().optional(),
  backstory: z.string().optional(),
  model: z.string().optional(),
});

export const agentsResponseSchema = z.object({
  agents: z.array(agentItemSchema).default([]),
});

export const assessResponseSchema = z.object({
  result: z.string().optional().default(""),
  report_id: z.string().optional().default(""),
});

export const chatResponseSchema = z.object({
  reply: z.string().optional().default(""),
});

export const decisionOptionSchema = z
  .object({
    id: z.string(),
    title: z.string(),
    why: z.string(),
    steps: z.array(z.string()).default([]),
    cost: z.string().default(""),
    impact: z.string().default(""),
    risk: z.string().default(""),
    depends_on: z.array(z.string()).default([]),
    acceptance_criteria: z.array(z.string()).default([]),
  })
  .passthrough();

export const optionsGenerateSchema = z.object({
  options: z.array(decisionOptionSchema).default([]),
  raw_reply: z.string().optional(),
});

export const optionsSynthesizeSchema = z.object({
  suggestion_markdown: z.string().optional().default(""),
});

export const patchReportSchema = z
  .object({
    ok: z.boolean().optional(),
    new_report_id: z.string().optional(),
  })
  .passthrough();

export const cloneRepoSchema = z.object({
  path: z.string(),
  slot: z.string().optional(),
  upload_id: z.string().optional(),
  url: z.string().optional(),
});

export const uploadZipSchema = z.object({
  path: z.string(),
  slot: z.string().optional(),
  upload_id: z.string().optional(),
  zip_name: z.string().optional(),
  bytes: z.number().optional(),
});

export const browseStateSchema = z.object({
  path: z.string(),
  parent: z.string().nullable(),
  entries: z.array(
    z.object({
      name: z.string(),
      path: z.string(),
      is_dir: z.boolean(),
    }),
  ),
});

export const createAgentSchema = z.object({
  agent: z
    .object({
      id: z.string().optional(),
    })
    .optional(),
});
