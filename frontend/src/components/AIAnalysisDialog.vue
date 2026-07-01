<script setup>
import { ref, watch } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps({
  modelValue: Boolean,
  loading: Boolean,
  analysis: Object,
  title: { type: String, default: 'AI 持仓分析' }
})

const emit = defineEmits(['update:modelValue', 'refresh'])

const dialogVisible = ref(false)

watch(() => props.modelValue, (val) => {
  dialogVisible.value = val
})

watch(dialogVisible, (val) => {
  if (!val) emit('update:modelValue', false)
})
</script>

<template>
  <el-dialog v-model="dialogVisible" :title="title" width="700px" top="5vh" destroy-on-close>
    <div v-if="loading" style="text-align:center;padding:60px 0">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p style="margin-top:16px;color:#999">AI 分析中，请稍候...</p>
    </div>
    <div v-else-if="analysis">
      <div v-if="analysis.created_at || analysis.is_cache" style="margin-bottom:12px;font-size:13px;color:#999;display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <span v-if="analysis.created_at">{{ analysis.created_at }}</span>
        <el-tag v-if="analysis.is_cache" size="small" type="info">缓存</el-tag>
        <el-tag v-else size="small" type="success">全新</el-tag>
        <el-button size="small" text type="primary" @click="$emit('refresh')">刷新分析</el-button>
      </div>
      <div v-if="analysis.summary" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:16px">
        <div v-for="(val,key) in analysis.summary" :key="key" style="background:#f9fafb;border-radius:8px;padding:10px;text-align:center">
          <div style="font-size:12px;color:#999;margin-bottom:4px">{{ key }}</div>
          <div style="font-size:16px;font-weight:600" :class="val.startsWith('-') ? 'negative' : 'positive'">{{ val }}</div>
        </div>
      </div>
      <div class="markdown-body" v-html="renderMarkdown(analysis.analysis)"></div>
    </div>
  </el-dialog>
</template>

<style scoped>
.positive { color: #dc2626 }
.negative { color: #16a34a }
:deep(.markdown-body) { font-size: 14px; line-height: 1.7 }
:deep(.markdown-body h3) { margin: 16px 0 8px; font-size: 16px; border-bottom: 1px solid #eee; padding-bottom: 6px }
:deep(.markdown-body p) { margin: 6px 0 }
:deep(.markdown-body ul) { padding-left: 20px }
:deep(.markdown-body li) { margin: 4px 0 }
</style>
