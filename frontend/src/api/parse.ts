import type { z } from "zod";

/** 驗證 API JSON，失敗時丟出可讀錯誤 */
export function parseApi<T>(schema: z.ZodType<T>, data: unknown, label = "回應"): T {
  const r = schema.safeParse(data);
  if (!r.success) {
    const msg = r.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ");
    throw new Error(`${label}格式不符：${msg}`);
  }
  return r.data;
}
