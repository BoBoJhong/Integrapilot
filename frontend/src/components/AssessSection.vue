<template>
  <section v-show="section === 'assess'">
    <el-card class="card">
      <template #header><h2 class="card-title">路徑設定</h2></template>
      <div class="stepper">
        <div class="step active"><strong>步驟 1</strong>ZIP、Git 或輸入／套用路徑</div>
        <div class="step"><strong>步驟 2</strong>必要時用下方瀏覽器確認</div>
        <div class="step"><strong>步驟 3</strong>開始評估並等待完成</div>
      </div>
      <p class="muted" style="margin-bottom: 10px">
        若 Docker 未掛載本機資料夾，可<strong>上傳 ZIP</strong>或<strong>貼 Git https URL</strong> clone；完成後路徑會自動帶入下方。
        私有庫請用含 token 的 https URL（回應中會隱藏憑證）。
      </p>
      <div class="zip-row">
        <el-upload
          :show-file-list="false"
          accept=".zip,application/zip"
          :http-request="handleZipA"
        >
          <el-button type="primary" plain :loading="zipUploadA">上傳專案 A（.zip）</el-button>
        </el-upload>
        <el-upload
          :show-file-list="false"
          accept=".zip,application/zip"
          :http-request="handleZipB"
        >
          <el-button type="primary" plain :loading="zipUploadB">上傳專案 B（.zip）</el-button>
        </el-upload>
      </div>
      <div class="git-clone-block">
        <div class="git-clone-row">
          <span class="git-label">專案 A · Git</span>
          <el-input v-model.trim="gitUrlA" placeholder="https://github.com/org/repo.git" clearable />
          <el-input v-model.trim="gitBranchA" placeholder="分支（可選，如 main）" clearable style="max-width: 200px" />
          <el-button type="success" plain :loading="gitCloneA" @click="cloneFromGit('a')">Clone</el-button>
        </div>
        <div class="git-clone-row">
          <span class="git-label">專案 B · Git</span>
          <el-input v-model.trim="gitUrlB" placeholder="https://github.com/org/repo.git" clearable />
          <el-input v-model.trim="gitBranchB" placeholder="分支（可選）" clearable style="max-width: 200px" />
          <el-button type="success" plain :loading="gitCloneB" @click="cloneFromGit('b')">Clone</el-button>
        </div>
      </div>
      <label for="pa">專案 A（容器內路徑）</label>
      <el-input id="pa" v-model.trim="projectA" placeholder="/projA" clearable />
      <label for="pb">專案 B（容器內路徑）</label>
      <el-input id="pb" v-model.trim="projectB" placeholder="/projB" clearable />
      <div class="row" style="margin-top: 12px">
        <el-button type="primary" :loading="loading" @click="submitForm">
          {{ loading ? "評估進行中…" : "開始整合評估" }}
        </el-button>
        <el-button :disabled="loading" @click="swapPaths">交換 A / B</el-button>
        <el-button :disabled="loading" @click="clearResult">清空結果</el-button>
      </div>
      <p class="muted" style="margin-top: 10px">路徑會儲存在瀏覽器，下次開啟會自動帶入。</p>
    </el-card>

    <el-card v-if="mounts.length" class="card">
      <template #header><h2 class="card-title">快速套用掛載路徑</h2></template>
      <div class="row">
        <el-button
          v-for="m in mounts"
          :key="'ap-' + m.key"
          plain
          @click="applyPath(m.key, m.resolved_path)"
        >
          套用 {{ m.label }}：{{ m.resolved_path }}
        </el-button>
      </div>
    </el-card>

    <el-card v-if="mounts.length || projectA || projectB" class="card">
      <template #header><h2 class="card-title">路徑瀏覽（僅顯示允許之根目錄下）</h2></template>
      <div class="split-browse">
        <div class="panel">
          <div class="panel-head">
            專案 A
            <el-button v-if="browseA.parent" size="small" text @click="loadList('a', browseA.parent)">上一層</el-button>
          </div>
          <p class="muted"><code class="path">{{ browseA.path || "—" }}</code></p>
          <ul class="file-list">
            <li v-for="e in browseA.entries" :key="'a' + e.path" @click="e.is_dir && loadList('a', e.path)">
              <span>{{ e.is_dir ? "📁" : "📄" }} {{ e.name }}</span>
              <el-button size="small" @click.stop="projectA = e.path">使用</el-button>
            </li>
          </ul>
        </div>
        <div class="panel">
          <div class="panel-head">
            專案 B
            <el-button v-if="browseB.parent" size="small" text @click="loadList('b', browseB.parent)">上一層</el-button>
          </div>
          <p class="muted"><code class="path">{{ browseB.path || "—" }}</code></p>
          <ul class="file-list">
            <li v-for="e in browseB.entries" :key="'b' + e.path" @click="e.is_dir && loadList('b', e.path)">
              <span>{{ e.is_dir ? "📁" : "📄" }} {{ e.name }}</span>
              <el-button size="small" @click.stop="projectB = e.path">使用</el-button>
            </li>
          </ul>
        </div>
      </div>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import type { ZipUploadOptions } from "@/types/workbench";
import { useWorkbenchStore } from "@/stores/workbench";

const wb = useWorkbenchStore();
const {
  browseA,
  browseB,
  gitBranchA,
  gitBranchB,
  gitCloneA,
  gitCloneB,
  gitUrlA,
  gitUrlB,
  loading,
  mounts,
  projectA,
  projectB,
  section,
  zipUploadA,
  zipUploadB,
} = storeToRefs(wb);

const {
  applyPath,
  cloneFromGit,
  clearResult,
  loadList,
  onZipUpload,
  submitForm,
  swapPaths,
} = wb;

function handleZipA(opts: unknown) {
  return onZipUpload("a", opts as ZipUploadOptions);
}
function handleZipB(opts: unknown) {
  return onZipUpload("b", opts as ZipUploadOptions);
}
</script>
