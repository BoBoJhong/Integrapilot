<template>
  <div class="shell">
    <aside class="sidebar" aria-label="主要導航">
      <div class="brand">
        IntegraPilot
        <small>Vue 3 · Vite · CrewAI</small>
      </div>
      <button type="button" class="nav-btn" :class="{ active: section === 'overview' }" @click="section = 'overview'">
        <el-icon><House /></el-icon> 概覽
      </button>
      <button type="button" class="nav-btn" :class="{ active: section === 'assess' }" @click="section = 'assess'">
        <el-icon><MagicStick /></el-icon> 建立評估
      </button>
      <button type="button" class="nav-btn" :class="{ active: section === 'reports' }" @click="section = 'reports'">
        <el-icon><Document /></el-icon> 報告與討論
      </button>
    </aside>

    <div class="main">
      <header class="topbar">
        <div>
          <h1>{{ sectionTitle }}</h1>
          <p class="desc">{{ sectionDesc }}</p>
        </div>
        <div class="row">
          <el-tag class="status-pill" :type="statusType" effect="light" :title="statusText">{{ statusText }}</el-tag>
          <el-button type="primary" plain @click="loadAll">同步資料</el-button>
        </div>
      </header>

      <main class="content">
        <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="global-alert" />

        <OverviewSection />
        <AssessSection />
        <ReportsSection />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Document, House, MagicStick } from "@element-plus/icons-vue";
import { storeToRefs } from "pinia";
import { onMounted } from "vue";
import AssessSection from "@/components/AssessSection.vue";
import OverviewSection from "@/components/OverviewSection.vue";
import ReportsSection from "@/components/ReportsSection.vue";
import { useWorkbenchStore } from "@/stores/workbench";

const wb = useWorkbenchStore();
const { error, section, sectionDesc, sectionTitle, statusText, statusType } = storeToRefs(wb);
const { loadAll } = wb;

onMounted(() => {
  void loadAll();
});
</script>
