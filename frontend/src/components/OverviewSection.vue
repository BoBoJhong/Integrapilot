<template>
  <section v-show="section === 'overview'">
    <el-card class="card">
      <template #header><h2 class="card-title">這個工具做什麼？</h2></template>
      <p class="muted">
        比對兩個專案目錄，產出整合評估 Markdown 報告；報告可存檔，並可在此與 Agent 依報告內容討論下一步。
        <strong>建議</strong>：在「建立評估」可<strong>上傳 ZIP</strong>或<strong>貼 Git https URL 執行 clone</strong>，不必設定 Docker 掛載；
        若用掛載則請填<strong>容器內路徑</strong>（例如 <code class="path">/projA</code>）。
      </p>
    </el-card>

    <el-card class="card">
      <template #header><h2 class="card-title">掛載狀態</h2></template>
      <p v-if="mountHint" class="muted">{{ mountHint }}</p>
      <div v-if="mounts.length" class="mount-grid">
        <div v-for="m in mounts" :key="m.key" class="mount-card">
          <div class="row" style="justify-content: space-between">
            <strong>{{ m.label }}</strong>
            <el-tag size="small" :type="m.exists ? 'success' : 'danger'">{{ m.exists ? "可讀" : "不存在" }}</el-tag>
          </div>
          <p class="muted" style="margin: 8px 0 4px">容器路徑</p>
          <code class="path">{{ m.resolved_path }}</code>
          <p v-if="m.host_hint" class="muted" style="margin: 8px 0 4px">主機提示</p>
          <code v-if="m.host_hint" class="path">{{ m.host_hint }}</code>
        </div>
      </div>
      <el-empty v-else description="目前沒有可用掛載資訊" :image-size="60" />
    </el-card>

    <el-card class="card">
      <template #header><h2 class="card-title">建議流程</h2></template>
      <div class="stepper">
        <div class="step active"><strong>1</strong>確認掛載與路徑</div>
        <div class="step"><strong>2</strong>建立評估</div>
        <div class="step"><strong>3</strong>閱讀報告並與 Agent 討論</div>
      </div>
      <div class="row">
        <el-button type="primary" @click="section = 'assess'">前往建立評估</el-button>
        <el-button @click="section = 'reports'">前往報告與討論</el-button>
      </div>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useWorkbenchStore } from "@/stores/workbench";

const wb = useWorkbenchStore();
const { mountHint, mounts, section } = storeToRefs(wb);
</script>
