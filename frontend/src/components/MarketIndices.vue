<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { marketAPI } from '@/api'
import { formatDateTime, formatDate } from '@/utils/format'

defineProps({
  indices: { type: Array, default: () => [] },
  indicesLoading: { type: Boolean, default: false },
  indicesDate: { type: String, default: '' },
  indicesIsToday: { type: Boolean, default: true },
  indicesUpdateTime: { type: String, default: '' }
})

const emit = defineEmits(['refresh'])

const showIndicesDialog = ref(false)
const availableIndices = ref([])
const selectedIndicesCodes = ref([])
const indicesSaving = ref(false)

const groupedIndices = computed(() => {
  const groups = { 'A股': [], '港股': [], '美股': [] }
  availableIndices.value.forEach(idx => {
    if (groups[idx.category]) {
      groups[idx.category].push(idx)
    }
  })
  return groups
})

async function openIndicesDialog() {
  showIndicesDialog.value = true
  try {
    const [availableRes, selectedRes] = await Promise.all([
      marketAPI.getAvailableIndices(),
      marketAPI.getSelectedIndices()
    ])
    availableIndices.value = availableRes.data || []
    selectedIndicesCodes.value = selectedRes.codes || []
  } catch (error) {
    console.error('加载指数配置失败:', error)
    ElMessage.error('加载指数配置失败')
  }
}

async function saveIndicesSelection() {
  if (selectedIndicesCodes.value.length === 0) {
    ElMessage.warning('请至少选择一个指数')
    return
  }
  if (selectedIndicesCodes.value.length > 6) {
    ElMessage.warning('最多只能选择6个指数')
    return
  }

  indicesSaving.value = true
  try {
    await marketAPI.saveSelectedIndices(selectedIndicesCodes.value)
    ElMessage.success('保存成功')
    showIndicesDialog.value = false
    emit('refresh')
  } catch (error) {
    console.error('保存指数选择失败:', error)
    ElMessage.error('保存失败')
  } finally {
    indicesSaving.value = false
  }
}
</script>

<template>
  <el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
    <div class="data-card">
      <div class="card-header">
        <span class="title">市场概况</span>
        <div class="header-actions">
          <span class="update-time" v-if="indicesUpdateTime">
            {{ formatDateTime(indicesUpdateTime) }}
          </span>
          <el-tag size="small" :type="indicesIsToday ? 'success' : 'info'" v-if="indices.length">
            {{ indicesIsToday ? '今日' : formatDate(indicesDate) }}
          </el-tag>
          <el-tooltip content="刷新数据" placement="top">
            <el-button size="small" circle @click="$emit('refresh')" :loading="indicesLoading">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="选择指数" placement="top">
            <el-button size="small" circle @click="openIndicesDialog">
              <el-icon><Setting /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>
      <div class="card-body">
        <div class="indices-grid" v-loading="indicesLoading">
          <div
            v-for="index in indices"
            :key="index.code"
            class="index-item"
            :class="{ up: index.change_pct > 0, down: index.change_pct < 0 }"
          >
            <div class="index-name">{{ index.name }}</div>
            <div class="index-price">{{ index.price?.toFixed(2) }}</div>
            <div class="index-change">
              <span>{{ index.change > 0 ? '+' : '' }}{{ index.change?.toFixed(2) }}</span>
              <span class="change-pct">{{ index.change_pct > 0 ? '+' : '' }}{{ index.change_pct?.toFixed(2) }}%</span>
            </div>
          </div>
          <el-empty v-if="!indicesLoading && indices.length === 0" description="暂无数据" :image-size="60" />
        </div>
      </div>
    </div>

    <el-dialog v-model="showIndicesDialog" title="选择展示指数" width="500px">
      <div class="indices-select-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>请选择最多 6 个指数展示在首页市场概况中</span>
      </div>
      <div class="indices-select-count">
        已选择 <strong>{{ selectedIndicesCodes.length }}</strong> / 6 个
      </div>
      <el-checkbox-group v-model="selectedIndicesCodes" class="indices-checkbox-group">
        <div v-for="(indices, category) in groupedIndices" :key="category" class="index-category">
          <div class="category-title">{{ category }}</div>
          <div class="category-options">
            <el-checkbox
              v-for="idx in indices"
              :key="idx.code"
              :label="idx.code"
              :disabled="selectedIndicesCodes.length >= 6 && !selectedIndicesCodes.includes(idx.code)"
            >
              {{ idx.name }}
            </el-checkbox>
          </div>
        </div>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="showIndicesDialog = false">取消</el-button>
        <el-button type="primary" @click="saveIndicesSelection" :loading="indicesSaving">保存</el-button>
      </template>
    </el-dialog>
  </el-col>
</template>

<style scoped>
@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.data-card {
  animation: scaleIn 0.4s ease-out backwards;
}

.data-card {
  background: #fff;
  border-radius: 16px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 6px 20px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  transition: all 0.3s;
  height: 340px;
  display: flex;
  flex-direction: column;
}

.data-card:hover {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.10);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.card-header .title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.card-body {
  padding: 16px 20px;
  flex: 1;
  min-height: 0;
}

.card-body .el-empty {
  padding: 40px 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.card-body .el-empty .el-empty__image {
  width: 80px;
  height: 80px;
  opacity: 0.6;
}

.card-body .el-empty .el-empty__description {
  margin-top: 16px;
  font-size: 13px;
  color: #909399;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.update-time {
  font-size: 12px;
  color: #909399;
}

.card-header .el-button.is-circle {
  background: #fff;
  border: 1px solid #e8eaed;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
}

.card-header .el-button.is-circle:hover {
  background: #f0f7ff;
  border-color: #1890ff;
  color: #1890ff;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.15);
  transform: translateY(-1px);
}

.indices-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 12px;
  height: 240px;
}

.index-item {
  text-align: center;
  padding: 12px 8px;
  background: #fff;
  border-radius: 10px;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border: 1px solid #f1f5f9;
  position: relative;
  overflow: hidden;
}

.index-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #94a3b8;
}

.index-item.up::before {
  background: #dc2626;
}

.index-item.down::before {
  background: #16a34a;
}

.index-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.index-name {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
  font-weight: 500;
}

.index-price {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 6px;
}

.index-change {
  font-size: 12px;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.index-item.up .index-price {
  color: #dc2626;
}

.index-item.down .index-price {
  color: #16a34a;
}

.index-item.up .index-change {
  color: #dc2626;
}

.index-item.down .index-change {
  color: #16a34a;
}

.change-pct {
  font-weight: 600;
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.index-item.up .change-pct {
  background: rgba(220, 38, 38, 0.1);
}

.index-item.down .change-pct {
  background: rgba(22, 163, 74, 0.1);
}

.indices-select-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  background: #f0f9ff;
  border-radius: 6px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #409eff;
}

.indices-select-count {
  margin-bottom: 16px;
  font-size: 13px;
  color: #606266;
}

.indices-select-count strong {
  color: #409eff;
}

.indices-checkbox-group {
  width: 100%;
}

.index-category {
  margin-bottom: 16px;
}

.category-title {
  font-size: 13px;
  font-weight: 600;
  color: #909399;
  margin-bottom: 8px;
  padding-left: 4px;
  border-left: 3px solid #409eff;
}

.category-options {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 20px;
}

.category-options .el-checkbox {
  margin-right: 0;
}
</style>
