<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  fund: Object,
  recommended: Array
})

const emit = defineEmits(['update:modelValue', 'saved'])

const etfCode = ref('')

watch(() => props.modelValue, (val) => {
  if (val) {
    etfCode.value = props.fund?.related_etf || ''
  }
})

function selectRecommendedEtf(code) {
  etfCode.value = code
}

function handleClose() {
  emit('update:modelValue', false)
}

function handleSave() {
  emit('saved', etfCode.value)
}

function handleClear() {
  emit('saved', null)
}
</script>

<template>
  <el-dialog :model-value="modelValue" title="设置关联 ETF" width="500px" @update:model-value="handleClose">
    <p class="hint">关联场内 ETF 可获取当日实时行情，辅助盘中决策</p>

    <div v-if="recommended && recommended.length > 0" class="recommended-section">
      <div class="section-label">推荐 ETF</div>
      <div class="recommended-list">
        <el-tag
          v-for="etf in recommended"
          :key="etf.code"
          :class="['recommended-tag', { selected: etfCode === etf.code }]"
          @click="selectRecommendedEtf(etf.code)"
        >
          {{ etf.code }} {{ etf.name }}
        </el-tag>
      </div>
    </div>

    <el-form label-width="100px" style="margin-top: 16px">
      <el-form-item label="ETF代码">
        <el-input v-model="etfCode" placeholder="输入6位ETF代码，如 515030" maxlength="6" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="danger" @click="handleClear">清除关联</el-button>
      <el-button type="primary" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.hint {
  color: #909399;
  font-size: 13px;
  margin-bottom: 16px;
}

.recommended-section {
  margin-bottom: 16px;
}

.section-label {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.recommended-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.recommended-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.recommended-tag:hover {
  background: #ecf5ff;
  color: #409eff;
  border-color: #b3d8ff;
}

.recommended-tag.selected {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}
</style>
