<script setup>
import { renderMarkdown } from '@/utils/markdown'

defineProps({
  aiData: Object,
  aiLoading: Boolean
})

const emit = defineEmits(['analyze'])

function handleAnalyze() {
  emit('analyze')
}
</script>

<template>
  <div class="info-card">
    <div class="info-header">
      <span class="section-title">AI 建议</span>
      <el-space>
        <el-tag v-if="aiData?.cached" type="success" size="small">缓存</el-tag>
        <el-button
          v-if="aiData"
          size="small"
          :loading="aiLoading"
          @click="handleAnalyze"
        >
          刷新分析
        </el-button>
        <el-button
          v-else
          type="primary"
          size="small"
          :loading="aiLoading"
          @click="handleAnalyze"
        >
          开始分析
        </el-button>
      </el-space>
    </div>
    <el-scrollbar v-if="aiData" height="350px" class="ai-result">
      <div v-if="aiData.timestamp" class="ai-time">
        分析时间: {{ new Date(aiData.timestamp).toLocaleString('zh-CN') }}
      </div>
      <div class="markdown-body" v-html="renderMarkdown(aiData.analysis)"></div>
    </el-scrollbar>
    <el-empty v-else description="点击分析按钮获取 AI 建议" :image-size="50" />
  </div>
</template>

<style scoped>
.info-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 6px 20px rgba(0, 0, 0, 0.04);
  transition: all 0.3s;
}

.info-card:hover {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.10);
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
}

.ai-result {
  background: #f8fafc;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.ai-time {
  font-size: 12px;
  color: #909399;
  margin-bottom: 16px;
  padding: 6px 12px;
  background: #fff;
  border-radius: 6px;
  display: inline-block;
  border: 1px solid #e4e7ed;
}

.cache-hint {
  color: #e6a23c;
  margin-left: 8px;
}

.markdown-body {
  line-height: 1.8;
  color: #24292f;
  font-size: 14px;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin-top: 20px;
  margin-bottom: 12px;
  font-weight: 600;
  line-height: 1.4;
  padding: 8px 12px;
  border-radius: 6px;
}

.markdown-body :deep(h1) {
  font-size: 1.1em;
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  color: #fff;
}

.markdown-body :deep(h2) {
  font-size: 1em;
  background: #e8f4ff;
  color: #1a1a2e;
  border-left: 4px solid #409eff;
}

.markdown-body :deep(h3) {
  font-size: 0.95em;
  background: #f0f9eb;
  color: #1a1a2e;
  border-left: 4px solid #67c23a;
}

.markdown-body :deep(h4) {
  font-size: 0.9em;
  background: #fdf6ec;
  color: #1a1a2e;
  border-left: 4px solid #e6a23c;
}

.markdown-body :deep(p) {
  margin-bottom: 12px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin-bottom: 12px;
  padding-left: 1.5em;
}

.markdown-body :deep(li) {
  margin-bottom: 4px;
}

.markdown-body :deep(strong) {
  font-weight: 600;
  color: #1a1a2e;
  background: #fff3cd;
  padding: 1px 4px;
  border-radius: 3px;
}

.markdown-body :deep(code) {
  background: rgba(175, 184, 193, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace;
}

.markdown-body :deep(pre) {
  background: #282c34;
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
  margin-bottom: 12px;
}

.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
  color: #abb2bf;
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid #409eff;
  padding: 8px 16px;
  margin: 12px 0;
  background: #f0f7ff;
  color: #57606a;
  border-radius: 0 6px 6px 0;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 12px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e8eaed;
  padding: 8px 12px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #0ea5e9;
  color: #fff;
  font-weight: 600;
}

.markdown-body :deep(tr:nth-child(even)) {
  background: #f6f8fa;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 2px solid #e8eaed;
  margin: 20px 0;
}

.markdown-body :deep(a) {
  color: #409eff;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}
</style>
