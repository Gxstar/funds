<script setup>
import { formatCurrency } from '@/utils/format'

defineProps({
  modelValue: Boolean,
  trades: Array,
  loading: Boolean
})

const emit = defineEmits(['update:modelValue', 'edit-trade', 'delete-trade'])

function handleClose() {
  emit('update:modelValue', false)
}

function handleEdit(trade) {
  emit('edit-trade', trade)
}

function handleDelete(tradeId) {
  emit('delete-trade', tradeId)
}
</script>

<template>
  <el-dialog :model-value="modelValue" title="交易记录" width="800px" @update:model-value="handleClose">
    <el-table :data="trades" max-height="400" style="width: 100%">
      <el-table-column prop="trade_date" label="购买时间" min-width="100" />
      <el-table-column prop="confirm_date" label="确认时间" min-width="100" />
      <el-table-column prop="trade_type" label="类型" width="70" align="center">
        <template #default="{ row }">
          <el-tag :type="row.trade_type === 'BUY' ? 'danger' : 'success'" size="small">
            {{ row.trade_type === 'BUY' ? '买入' : '卖出' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="confirm_net_value" label="确认净值" min-width="90" align="right">
        <template #default="{ row }">{{ row.confirm_net_value ? parseFloat(row.confirm_net_value).toFixed(4) : '-' }}</template>
      </el-table-column>
      <el-table-column prop="confirm_shares" label="确认份额" min-width="90" align="right">
        <template #default="{ row }">{{ row.confirm_shares ? parseFloat(row.confirm_shares).toFixed(2) : '-' }}</template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" min-width="100" align="right">
        <template #default="{ row }">{{ formatCurrency(row.amount) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="130" align="center">
        <template #default="{ row }">
          <el-space :size="4">
            <el-button size="small" text type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="handleDelete(row.id)">删除</el-button>
          </el-space>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>
