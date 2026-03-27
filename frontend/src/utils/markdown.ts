import DOMPurify from "dompurify";
import { marked } from "marked";

export function sanitizeMd(md: string): string {
  if (!md) return "";
  const raw = marked.parse(md, { breaks: true }) as string;
  return DOMPurify.sanitize(raw);
}
