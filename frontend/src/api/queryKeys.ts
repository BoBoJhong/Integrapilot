/** TanStack Query 鍵（集中管理，便於 invalidate） */
export const queryKeys = {
  mounts: ["mounts"] as const,
  reports: ["reports"] as const,
  agents: ["agents"] as const,
  report: (id: string) => ["report", id] as const,
};
