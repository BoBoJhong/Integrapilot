/**
 * 型別與 store 匯出（相容舊路徑 `@/composables/useAppState`）。
 * 元件請優先：`import { useWorkbenchStore } from '@/stores/workbench'` 並搭配 `storeToRefs`。
 */
export type * from "@/types/workbench";
export { useWorkbenchStore } from "@/stores/workbench";
