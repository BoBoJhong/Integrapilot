/** 後端 JSON 錯誤常見形狀 */
export interface ApiErrorBody {
  detail?: string | unknown;
}

export async function fetchJson<T = unknown>(
  url: string,
  options?: RequestInit,
): Promise<{ res: Response; data: T }> {
  const res = await fetch(url, options);
  const text = await res.text();
  let data: T = null as T;
  try {
    data = (text ? JSON.parse(text) : null) as T;
  } catch {
    const preview = text.replace(/\s+/g, " ").trim().slice(0, 280);
    throw new Error(`回應不是 JSON（HTTP ${res.status}）：${preview}`);
  }
  return { res, data };
}

export async function postFormData<T = unknown>(
  url: string,
  formData: FormData,
): Promise<{ res: Response; data: T }> {
  const res = await fetch(url, { method: "POST", body: formData });
  const text = await res.text();
  let data: T = null as T;
  try {
    data = (text ? JSON.parse(text) : null) as T;
  } catch {
    const preview = text.replace(/\s+/g, " ").trim().slice(0, 280);
    throw new Error(`回應不是 JSON（HTTP ${res.status}）：${preview}`);
  }
  return { res, data };
}

export function detailMessage(data: unknown): string {
  if (data && typeof data === "object" && "detail" in data) {
    const d = (data as ApiErrorBody).detail;
    if (typeof d === "string") return d;
    if (d !== undefined) return JSON.stringify(d);
  }
  return "請求失敗";
}
