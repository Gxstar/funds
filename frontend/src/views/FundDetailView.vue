<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useFundStore } from '@/stores/funds'
import { useChartStore } from '@/stores/chart'
import { useAIStore } from '@/stores/ai'


import FundHeader from '@/components/FundHeader.vue'
import HoldingCard from '@/components/HoldingCard.vue'
import ETFCard from '@/components/ETFCard.vue'
import NavChart from '@/components/NavChart.vue'
import AIPanel from '@/components/AIPanel.vue'
import TradeFormDialog from '@/components/TradeFormDialog.vue'
import HoldingFormDialog from '@/components/HoldingFormDialog.vue'
import ETFFormDialog from '@/components/ETFFormDialog.vue'
import TradeHistoryDialog from '@/components/TradeHistoryDialog.vue'

const route = useRoute()
const router = useRouter()
const fundStore = useFundStore()
const chartStore = useChartStore()
const aiStore = useAIStore()

const loading = ref(true)
const period = ref('1y')

const tradeDialogVisible = ref(false)
const tradeType = ref('BUY')
const holdingDialogVisible = ref(false)
const etfDialogVisible = ref(false)
const tradeHistoryVisible = ref(false)
const editingTrade = ref(null)

const etfRefreshing = ref(false)
const syncingFund = ref(false)
const recommendedEtfs = ref([])

const fund = computed(() => fundStore.currentFund)

const holdingInfo = computed(() => {
  if (!fund.value?.total_shares || parseFloat(fund.value.total_shares) <= 0) return null
  const shares = parseFloat(fund.value.total_shares)
  const costPrice = parseFloat(fund.value.cost_price)
  const totalCost = parseFloat(fund.value.total_cost)
  const currentNetValue = parseFloat(fund.value.last_net_value || 0)
  const marketValue = shares * currentNetValue
  const profit = marketValue - totalCost
  const profitRate = totalCost ? (profit / totalCost * 100) : 0
  return { shares, costPrice, totalCost, currentNetValue, marketValue, profit, profitRate }
})

async function loadFundData() {
  const code = route.params.code
  if (!code) return
  loading.value = true
  try {
    await fundStore.selectFund(code)
    await aiStore.loadAICache(code)
  } catch (error) {
    ElMessage.error('加载基金详情失败')
    router.push('/')
  } finally {
    loading.value = false
  }
}

function showTradeDialog(type) {
  tradeType.value = type
  editingTrade.value = null
  tradeDialogVisible.value = true
}

async function handleTradeSaved(data) {
  try {
    if (data.isEdit) {
      await fundStore.updateTrade(data.id, {
        trade_type: data.trade_type,
        trade_date: data.trade_date,
        confirm_date: data.confirm_date || null,
        amount: data.amount,
        confirm_net_value: data.confirm_net_value || null,
        confirm_shares: data.confirm_shares || null,
        fund_code: route.params.code
      })
      if (tradeHistoryVisible.value) {
        const result = await chartStore.loadTradeHistory(route.params.code, 100)
        allTrades.value = result.data || []
      }
    } else {
      await fundStore.addTrade({
        fund_code: route.params.code,
        trade_type: tradeType.value,
        trade_date: data.trade_date,
        confirm_date: data.confirm_date,
        amount: data.amount,
        confirm_net_value: data.confirm_net_value,
        confirm_shares: data.confirm_shares
      })
    }
    tradeDialogVisible.value = false
    ElMessage.success('交易记录已保存')
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  }
}

function showHoldingDialog() {
  holdingDialogVisible.value = true
}

async function handleHoldingSaved(data) {
  try {
    await fundStore.updateHolding(route.params.code, data)
    holdingDialogVisible.value = false
    ElMessage.success('持仓已保存')
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  }
}

async function handleHoldingClear() {
  try {
    await ElMessageBox.confirm('确定要清空该基金的持仓吗？', '警告', { type: 'warning' })
    await fundStore.updateHolding(route.params.code, { total_shares: '0', cost_price: '0', total_cost: '0' })
    holdingDialogVisible.value = false
    ElMessage.success('持仓已清空')
  } catch (e) {}
}

async function showETFDialog() {
  if (fund.value?.fund_type) {
    try {
      const result = await chartStore.getRecommendedETF(fund.value.fund_type)
      recommendedEtfs.value = result.data || []
    } catch (error) {
      recommendedEtfs.value = []
    }
  }
  etfDialogVisible.value = true
}

async function handleETFSaved(etfCode) {
  try {
    await fundStore.setRelatedETF(route.params.code, etfCode)
    etfDialogVisible.value = false
    ElMessage.success(etfCode ? 'ETF 关联已保存' : 'ETF 关联已清除')
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  }
}

const allTrades = ref([])

async function showTradeHistory() {
  try {
    const result = await chartStore.loadTradeHistory(route.params.code, 100)
    allTrades.value = result.data || []
  } catch (error) {
    allTrades.value = []
  }
  tradeHistoryVisible.value = true
}

function handleEditTrade(trade) {
  editingTrade.value = trade
  tradeType.value = trade.trade_type
  tradeDialogVisible.value = true
}

async function handleDeleteTrade(tradeId) {
  try {
    await ElMessageBox.confirm('确定删除该交易记录？', '警告', { type: 'warning' })
    await fundStore.deleteTrade(tradeId, route.params.code)
    const result = await chartStore.loadTradeHistory(route.params.code, 100)
    allTrades.value = result.data || []
    ElMessage.success('交易记录已删除')
  } catch (e) {}
}

async function handlePeriodChange(p) {
  period.value = p
  await chartStore.loadChartData(route.params.code, p)
}

async function refreshETF() {
  if (!fund.value?.related_etf) return
  etfRefreshing.value = true
  try {
    await chartStore.refreshETFData(fund.value.related_etf)
    ElMessage.success('ETF行情已刷新')
  } catch (error) {
    ElMessage.error(error.message || '刷新失败')
  } finally {
    etfRefreshing.value = false
  }
}

async function syncFundData() {
  if (!route.params.code) return
  syncingFund.value = true
  try {
    const result = await fundStore.syncFundData(route.params.code)
    if (result.status === 'success') {
      ElMessage.success(`同步成功，更新 ${result.count || 0} 条记录`)
      await fundStore.selectFund(route.params.code)
      await chartStore.loadChartData(route.params.code, period.value)
    } else if (result.status === 'skipped') {
      ElMessage.info(result.message || '数据已是最新')
    } else {
      throw new Error(result.error || '同步失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '同步失败')
  } finally {
    syncingFund.value = false
  }
}

async function getAIAnalysis(forceRefresh = false) {
  try {
    await aiStore.getAISuggestion(route.params.code, forceRefresh)
  } catch (error) {
    ElMessage.error(error.message || '分析失败')
  }
}

const emit = defineEmits(['delete-fund'])

async function deleteFund() {
  try {
    await ElMessageBox.confirm('确定要删除该基金吗？这将同时删除相关的持仓和交易记录。', '警告', { type: 'warning' })
    emit('delete-fund', route.params.code)
  } catch (e) {}
}

watch(() => route.params.code, (newCode, oldCode) => {
  if (!newCode) return
  if (oldCode && newCode !== oldCode) {
    aiStore.clearAIAnalysis()
  }
  loadFundData()
}, { immediate: true })
</script>

<template>
  <div v-loading="loading" class="fund-detail">
    <FundHeader :fund="fund" :holding="holdingInfo" @set-etf="showETFDialog" @delete="deleteFund" />

    <el-row :gutter="24">
      <el-col :span="fund?.related_etf ? 12 : 24">
        <HoldingCard :fund="fund" :holding="holdingInfo" @buy="showTradeDialog('BUY')" @sell="showTradeDialog('SELL')" @set-holding="showHoldingDialog" @show-trades="showTradeHistory" />
      </el-col>
      <el-col v-if="fund?.related_etf" :span="12">
        <ETFCard :etf-data="chartStore.etfData" :etf-code="fund.related_etf" :refreshing="etfRefreshing" @set-etf="showETFDialog" @refresh="refreshETF" />
      </el-col>
    </el-row>

    <el-row :gutter="24">
      <el-col :span="12">
        <NavChart :chart-data="chartStore.chartData" :period="period" :syncing="syncingFund" @update:period="handlePeriodChange" @sync="syncFundData" />
      </el-col>
      <el-col :span="12">
        <AIPanel :ai-data="aiStore.aiAnalysis" :ai-loading="aiStore.aiLoading" @analyze="getAIAnalysis(true)" />
      </el-col>
    </el-row>

    <TradeFormDialog v-model="tradeDialogVisible" :trade-type="tradeType" :fund="fund" :trade-to-edit="editingTrade" @saved="handleTradeSaved" />
    <HoldingFormDialog v-model="holdingDialogVisible" :fund="fund" @saved="handleHoldingSaved" @clear="handleHoldingClear" />
    <ETFFormDialog v-model="etfDialogVisible" :fund="fund" :recommended="recommendedEtfs" @saved="handleETFSaved" />
    <TradeHistoryDialog v-model="tradeHistoryVisible" :trades="allTrades" @edit-trade="handleEditTrade" @delete-trade="handleDeleteTrade" />
  </div>
</template>

<style scoped>
.fund-detail {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 900px;
  max-width: 1400px;
  gap: 16px;
}

.indicators-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.indicator-tag {
  display: flex;
  align-items: center;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  font-size: 13px;
}

.indicator-label {
  background: #e0f2fe;
  color: #0369a1;
  padding: 4px 10px;
  font-weight: 500;
}

.indicator-value {
  padding: 4px 12px;
  color: #1e293b;
  font-weight: 600;
  font-family: ui-monospace, SFMono-Regular, monospace;
}

.fund-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fund-name {
  font-size: 18px;
  font-weight: 600;
}

.mb-3 { margin-bottom: 12px; }
</style>
