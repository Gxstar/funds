<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  fund: Object
})

const emit = defineEmits(['update:modelValue', 'saved', 'clear'])

const form = ref({
  total_shares: '',
  cost_price: '',
  total_cost: ''
})

watch(() => props.modelValue, (val) => {
  if (val) {
    form.value = {
      total_shares: props.fund?.total_shares || '',
      cost_price: props.fund?.cost_price || '',
      total_cost: props.fund?.total_cost || ''
    }
  }
})

function calculateTotalCost() {
  const shares = parseFloat(form.value.total_shares)
  const costPrice = parseFloat(form.value.cost_price)
  if (shares && costPrice) {
    form.value.total_cost = (shares * costPrice).toFixed(2)
  }
}

function handleClose() {
  emit('update:modelValue', false)
}

function handleSave() {
  emit('saved', { ...form.value })
}

function handleClear() {
  emit('clear')
}
</script>

<template>
  <el-dialog :model-value="modelValue" title="设置持仓" width="450px" @update:model-value="handleClose">
    <p class="hint">直接设置持仓信息，无需逐笔录入交易记录</p>
    <el-form label-width="100px">
      <el-form-item label="持有份额">
        <el-input v-model="form.total_shares" placeholder="份额" @input="calculateTotalCost" />
      </el-form-item>
      <el-form-item label="成本价">
        <el-input v-model="form.cost_price" placeholder="单位净值" @input="calculateTotalCost" />
      </el-form-item>
      <el-form-item label="总投入">
        <el-input v-model="form.total_cost" placeholder="自动计算或手动输入" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="danger" @click="handleClear">清空持仓</el-button>
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
</style>
