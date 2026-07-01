<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  tradeType: String,
  fund: Object,
  tradeToEdit: Object
})

const emit = defineEmits(['update:modelValue', 'saved'])

const isEdit = computed(() => !!props.tradeToEdit)

const title = computed(() => {
  if (props.tradeToEdit) return '编辑交易记录'
  return props.tradeType === 'BUY' ? '买入' : '卖出'
})

const form = ref({
  trade_type: 'BUY',
  trade_date: '',
  confirm_date: '',
  amount: '',
  confirm_net_value: '',
  confirm_shares: ''
})

watch(() => props.modelValue, (val) => {
  if (val) {
    if (props.tradeToEdit) {
      form.value = {
        trade_type: props.tradeToEdit.trade_type,
        trade_date: props.tradeToEdit.trade_date,
        confirm_date: props.tradeToEdit.confirm_date || '',
        amount: String(props.tradeToEdit.amount),
        confirm_net_value: props.tradeToEdit.confirm_net_value ? String(props.tradeToEdit.confirm_net_value) : '',
        confirm_shares: props.tradeToEdit.confirm_shares ? String(props.tradeToEdit.confirm_shares) : ''
      }
    } else {
      const today = new Date().toISOString().split('T')[0]
      form.value = {
        trade_type: props.tradeType || 'BUY',
        trade_date: today,
        confirm_date: today,
        amount: '',
        confirm_net_value: '',
        confirm_shares: ''
      }
    }
  }
})

function calculateShares() {
  const amount = parseFloat(form.value.amount)
  const netValue = parseFloat(form.value.confirm_net_value)
  if (amount && netValue) {
    form.value.confirm_shares = (amount / netValue).toFixed(2)
  }
}

function handleClose() {
  emit('update:modelValue', false)
}

function handleSave() {
  emit('saved', {
    isEdit: isEdit.value,
    id: props.tradeToEdit?.id,
    trade_type: form.value.trade_type,
    trade_date: form.value.trade_date,
    confirm_date: form.value.confirm_date,
    amount: form.value.amount,
    confirm_net_value: form.value.confirm_net_value,
    confirm_shares: form.value.confirm_shares
  })
}
</script>

<template>
  <el-dialog :model-value="modelValue" :title="title" width="450px" @update:model-value="handleClose">
    <el-form label-width="100px">
      <el-form-item v-if="isEdit" label="交易类型">
        <el-select v-model="form.trade_type" style="width: 100%">
          <el-option value="BUY" label="买入" />
          <el-option value="SELL" label="卖出" />
        </el-select>
      </el-form-item>
      <el-form-item label="购买时间">
        <el-date-picker v-model="form.trade_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="确认时间">
        <el-date-picker v-model="form.confirm_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="金额">
        <el-input v-model="form.amount" placeholder="成交金额" @input="calculateShares" />
      </el-form-item>
      <el-form-item label="确认净值">
        <el-input v-model="form.confirm_net_value" placeholder="确认日净值" @input="calculateShares" />
      </el-form-item>
      <el-form-item label="确认份额">
        <el-input v-model="form.confirm_shares" placeholder="自动计算或手动输入" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleSave">确认</el-button>
    </template>
  </el-dialog>
</template>
