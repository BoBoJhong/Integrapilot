<template>
  <section v-show="section === 'reports'">
    <div class="reports-workbench">
      <div class="report-list-col">
        <el-card class="card">
          <template #header>
            <div class="row" style="justify-content: space-between">
              <h2 class="card-title" style="margin: 0">報告</h2>
              <el-button size="small" @click="loadReports">重新整理</el-button>
            </div>
          </template>
          <el-empty v-if="!reports.length" description="尚無報告，請先建立評估" :image-size="72" />
          <ul v-else class="report-list">
            <li
              v-for="r in reports"
              :key="r.id"
              :class="{ selected: activeReportId === r.id }"
              @click="openReport(r.id)"
            >
              <code class="path" style="font-size: 11px">{{ r.name }}</code>
              <div class="report-meta">{{ fmtTime(r.updated_at) }} · {{ r.size }} B</div>
            </li>
          </ul>
        </el-card>
      </div>

      <div class="report-pane">
        <el-card class="card">
          <template #header>
            <div class="row" style="justify-content: space-between">
              <h2 class="card-title" style="margin: 0">報告內容</h2>
              <div class="row">
                <el-button :disabled="!result" @click="downloadResult">下載 .md</el-button>
                <el-button :disabled="!result" :loading="exportWordLoading" type="primary" plain @click="downloadWord">
                  匯出 Word
                </el-button>
                <el-button :disabled="!result" @click="copy(result)">複製</el-button>
              </div>
            </div>
          </template>
          <el-tabs v-model="reportTab">
            <el-tab-pane label="預覽" name="preview">
              <div v-if="!result" class="empty">選擇左欄報告，或先執行「建立評估」。</div>
              <div v-else class="md-preview" v-html="renderedReport" />
            </el-tab-pane>
            <el-tab-pane label="Markdown" name="source">
              <textarea class="raw-md" readonly :value="result" placeholder="尚未載入報告" />
            </el-tab-pane>
          </el-tabs>
        </el-card>
        <el-card class="card">
          <template #header>
            <div class="row" style="justify-content: space-between">
              <h2 class="card-title" style="margin: 0">決策選項助手</h2>
              <div class="row">
                <el-button type="primary" plain :loading="optionLoading" @click="generateOptions">產生選項</el-button>
                <el-button :loading="suggestionLoading" :disabled="!decisionOptions.length" @click="synthesizeOptions">
                  綜合建議
                </el-button>
                <el-button
                  type="success"
                  plain
                  :loading="patchLoading"
                  :disabled="!suggestionMarkdown || !activeReportId"
                  @click="patchReportBySuggestion"
                >
                  套用到報告
                </el-button>
              </div>
            </div>
          </template>

          <div class="quick-action-row">
            <span class="quick-action-label">快速開始：</span>
            <el-button size="small" @click="runQuickAction('請根據目前內容，提供 3 個可執行的下一步，並附上優先順序理由')">
              幫我想下一步
            </el-button>
            <el-button size="small" @click="runQuickAction('我想評估功能面，請提供 3 個方案按風險/效益排序')">
              評估功能面
            </el-button>
            <el-button size="small" @click="runQuickAction('我想先快速落地，請給低成本且兩週內可完成的方案')">
              兩週內可做
            </el-button>
          </div>

          <el-input
            v-model="optionPrompt"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 5 }"
            placeholder="補充限制或偏好（可選），例如：工期 2 週內、先處理高風險。"
            style="margin-bottom: 10px"
          />

          <div v-if="decisionOptions.length" class="agent-create-form">
            <div v-for="opt in decisionOptions" :key="opt.id" class="panel">
              <div class="row" style="justify-content: space-between; align-items: flex-start">
                <el-checkbox
                  :model-value="selectedOptionIds.includes(opt.id)"
                  @change="(v: unknown) => toggleOptionSelected(opt.id, Boolean(v))"
                >
                  <strong>{{ opt.title }}</strong>
                </el-checkbox>
                <div class="row">
                  <el-tag size="small">{{ opt.impact }}</el-tag>
                  <el-tag size="small" type="warning">{{ opt.cost }}</el-tag>
                  <el-button
                    size="small"
                    text
                    :disabled="!selectedOptionIds.includes(opt.id)"
                    @click="moveSelectedOption(opt.id, 'up')"
                  >
                    ↑
                  </el-button>
                  <el-button
                    size="small"
                    text
                    :disabled="!selectedOptionIds.includes(opt.id)"
                    @click="moveSelectedOption(opt.id, 'down')"
                  >
                    ↓
                  </el-button>
                </div>
              </div>
              <p class="muted" style="margin-top: 8px">{{ opt.why }}</p>
              <ul class="muted" style="margin: 6px 0 0 18px">
                <li v-for="(s, i) in opt.steps" :key="`${opt.id}-step-${i}`">{{ s }}</li>
              </ul>
            </div>
          </div>
          <el-empty v-else description="先按「產生選項」，再勾選你要的方案。" :image-size="48" />

          <el-divider />
          <h3 class="card-title" style="font-size: 14px; margin: 0 0 8px">綜合建議（草稿）</h3>
          <textarea
            class="raw-md"
            style="min-height: 180px; max-height: 280px"
            :value="suggestionMarkdown"
            readonly
            placeholder="按「綜合建議」後會在這裡出現。"
          />
        </el-card>
      </div>

      <div class="agent-chat-panel" aria-label="Agent 對話">
        <header class="agent-chat-header">
          <div class="agent-chat-title-row">
            <div class="agent-chat-icon-wrap" aria-hidden="true">
              <el-icon :size="22"><ChatDotRound /></el-icon>
            </div>
            <div>
              <h3 class="agent-chat-title">與 Agent 對話</h3>
              <p class="agent-chat-desc">
                依目前報告內容回覆 ·
                <span class="agent-chat-agent-name">{{ selectedAgentLabel }}</span>
              </p>
            </div>
          </div>
        </header>

        <div class="agent-chat-toolbar">
          <el-select v-model="selectedAgentId" placeholder="選擇 Agent" class="agent-chat-select">
            <el-option v-for="a in agents" :key="a.id" :label="a.name" :value="a.id" />
          </el-select>
          <div class="agent-chat-toolbar-actions">
            <el-button size="small" @click="showAgentForm = !showAgentForm">
              {{ showAgentForm ? "收合表單" : "建立 Agent" }}
            </el-button>
            <el-button
              size="small"
              type="danger"
              plain
              :disabled="!selectedAgentId || selectedAgentId === 'integration-advisor'"
              @click="removeAgent"
            >
              刪除
            </el-button>
          </div>
        </div>

        <div v-if="showAgentForm" class="agent-create-card">
          <div class="agent-create-form">
            <el-input v-model.trim="newAgent.name" placeholder="Agent 名稱（例如：安全審查員）" />
            <el-input v-model.trim="newAgent.role" placeholder="角色（role）" />
            <el-input v-model.trim="newAgent.goal" placeholder="目標（goal）" />
            <el-input
              v-model.trim="newAgent.backstory"
              type="textarea"
              :rows="3"
              placeholder="背景與風格（backstory）"
            />
            <el-input v-model.trim="newAgent.model" placeholder="模型（可留空，用 .env MODEL）" />
            <el-button size="small" type="primary" :loading="agentSaving" @click="createAgent">儲存 Agent</el-button>
          </div>
        </div>

        <div ref="chatLogEl" class="agent-chat-messages">
          <div v-if="!chatMessages.length && !chatLoading" class="agent-chat-empty">
            <el-icon class="agent-chat-empty-icon" :size="44"><ChatLineRound /></el-icon>
            <p class="agent-chat-empty-title">載入報告後可在此提問</p>
            <p class="agent-chat-empty-hint">例如：「請把高風險項目排成兩週計畫」</p>
          </div>

          <div
            v-for="(m, idx) in chatMessages"
            :key="idx"
            class="chat-msg"
            :class="m.role === 'user' ? 'chat-msg--user' : 'chat-msg--assistant'"
          >
            <el-avatar v-if="m.role === 'user'" :size="36" class="chat-msg-avatar chat-msg-avatar--user">
              <el-icon><User /></el-icon>
            </el-avatar>
            <el-avatar v-else :size="36" class="chat-msg-avatar chat-msg-avatar--assistant">
              {{ selectedAgentInitial }}
            </el-avatar>
            <div class="chat-msg-body">
              <div class="chat-msg-meta">
                <span class="chat-msg-label">{{ m.role === "user" ? "你" : selectedAgentLabel }}</span>
              </div>
              <div class="chat-msg-bubble">{{ m.content }}</div>
            </div>
          </div>

          <div v-if="chatLoading" class="chat-msg chat-msg--assistant chat-msg--typing">
            <el-avatar :size="36" class="chat-msg-avatar chat-msg-avatar--assistant">
              {{ selectedAgentInitial }}
            </el-avatar>
            <div class="chat-msg-body">
              <div class="chat-msg-meta">
                <span class="chat-msg-label">{{ selectedAgentLabel }}</span>
              </div>
              <div class="chat-msg-bubble chat-msg-bubble--typing">
                <el-icon class="chat-typing-icon is-loading"><Loading /></el-icon>
                思考中…
              </div>
            </div>
          </div>
        </div>

        <footer class="agent-chat-footer">
          <el-input
            v-model="chatInput"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 8 }"
            resize="none"
            placeholder="輸入問題…（Enter 送出，Shift+Enter 換行）"
            class="agent-chat-textarea"
            @keydown="onChatKeydown"
          />
          <div class="agent-chat-footer-row">
            <span class="agent-chat-kbd-hint">Enter 送出 · Shift+Enter 換行</span>
            <div class="agent-chat-footer-btns">
              <el-button type="danger" plain :disabled="chatLoading || !chatMessages.length" @click="clearChat">
                清空
              </el-button>
              <el-button type="primary" :loading="chatLoading" @click="sendChat">送出</el-button>
            </div>
          </div>
        </footer>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ChatDotRound, ChatLineRound, Loading, User } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { useWorkbenchStore } from "@/stores/workbench";

const wb = useWorkbenchStore();
const {
  activeReportId,
  agentSaving,
  agents,
  chatInput,
  chatLoading,
  chatLogEl,
  chatMessages,
  decisionOptions,
  exportWordLoading,
  newAgent,
  optionLoading,
  optionPrompt,
  patchLoading,
  renderedReport,
  reportTab,
  reports,
  result,
  section,
  selectedAgentId,
  selectedAgentInitial,
  selectedAgentLabel,
  selectedOptionIds,
  showAgentForm,
  suggestionLoading,
  suggestionMarkdown,
} = storeToRefs(wb);

const {
  clearChat,
  copy,
  createAgent,
  downloadResult,
  downloadWord,
  fmtTime,
  generateOptions,
  loadReports,
  moveSelectedOption,
  onChatKeydown,
  openReport,
  patchReportBySuggestion,
  removeAgent,
  sendChat,
  synthesizeOptions,
  toggleOptionSelected,
} = wb;

async function runQuickAction(prompt: string): Promise<void> {
  optionPrompt.value = prompt;
  await generateOptions();
  if (decisionOptions.value.length) {
    ElMessage.success("已為你產生可選按鈕方案，請勾選下一步");
  }
}
</script>
