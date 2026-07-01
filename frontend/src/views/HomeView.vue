<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/funds'
import { useHoldingStore } from '@/stores/holdings'
import { useAIStore } from '@/stores/ai'

import AIAnalysisDialog from '@/components/AIAnalysisDialog.vue'
import DashboardStats from '@/components/DashboardStats.vue'
import MarketIndices from '@/components/MarketIndices.vue'
import PortfolioDistributionChart from '@/components/PortfolioDistributionChart.vue'
import PortfolioHistoryChart from '@/components/PortfolioHistoryChart.vue'
import HoldingsTable from '@/components/HoldingsTable.vue'
import RecentTrades from '@/components/RecentTrades.vue'
import ChangeRanking from '@/components/ChangeRanking.vue'

const router = useRouter()
const fundStore = useFundStore()
const holdingStore = useHoldingStore()
const aiStore = useAIStore()

const portfolioLoading = ref(false)
const portfolioAnalysis = ref(null)

const portfolioHistory = ref({
  dates: [],
  market_values: [],
  costs: [],
  profits: [],
  profit_rates: []
})
const portfolioHistoryLoading = ref(false)

const indicesData = ref([])
const indicesLoading = ref(false)
const indicesDate = ref('')
const indicesIsToday = ref(true)
const indicesUpdateTime = ref('')

const syncingAll = ref(false)

const positionInfo = computed(() => {
  const total = parseFloat(aiStore.aiSettings?.total_position_amount) || 0
  const market = holdingStore.holdingsSummary.total_market_value
  if (total > 0) {
    const ratio = (market / total * 100).toFixed(1)
    const available = total - market
    return { ratio, available, total }
  }
  return null
})

const showAnalysisDialog = computed({
  get: () => portfolioLoading.value || !!portfolioAnalysis.value,
  set: (val) => { if (!val) portfolioAnalysis.value = null }
})

async function loadPortfolioHistory() {
  portfolioHistoryLoading.value = true
  try {
    const result = await holdingStore.loadPortfolioHistory(90)
    portfolioHistory.value = result
  } catch (error) {
    console.error('加载持仓历史收益失败:', error)
  } finally {
    portfolioHistoryLoading.value = false
  }
}

async function loadIndices(skipCache = false) {
  indicesLoading.value = true
  try {
    const result = await fundStore.loadIndices(skipCache)
    indicesData.value = result.data || []
    indicesDate.value = result.date || ''
    indicesIsToday.value = result.is_today !== false
    indicesUpdateTime.value = result.update_time || ''
  } catch (error) {
    console.error('加载市场指数 failed:', error)
  } finally {
    indicesLoading.value = false
  }
}

async function refreshIndices() {
  await loadIndices(true)
}

async function syncAllFunds() {
  syncingAll.value = true
  try {
    const result = await fundStore.syncAll()
    const successCount = result.results?.filter(r => r.status === 'success').length || 0
    const failedCount = result.results?.filter(r => r.status === 'failed').length || 0

    if (failedCount > 0) {
      ElMessage.warning(`同步完成：成功 ${successCount} 只，失败 ${failedCount} 只`)
    } else {
      ElMessage.success(`同步完成：成功 ${successCount} 只基金`)
    }

    await Promise.all([
      fundStore.loadFunds(),
      holdingStore.loadHoldingsSummary()
    ])
  } catch (error) {
    ElMessage.error(error.message || '同步失败')
  } finally {
    syncingAll.value = false
  }
}

async function loadPortfolioAnalysis() {
  portfolioLoading.value = true
  try {
    const result = await aiStore.analyzePortfolio(false, true)
    if (result.no_cache) {
      portfolioAnalysis.value = null
    } else {
      portfolioAnalysis.value = result
    }
  } catch (error) {
    console.error('加载分析缓存失败:', error)
  } finally {
    portfolioLoading.value = false
  }
}

async function refreshPortfolioAnalysis() {
  portfolioLoading.value = true
  try {
    const result = await aiStore.analyzePortfolio(true, false)
    if (result.error) throw new Error(result.error)
    portfolioAnalysis.value = result
  } catch (error) {
    ElMessage.error(error.message || '分析失败')
  } finally {
    portfolioLoading.value = false
  }
}

async function openAnalysisDialog() {
  await loadPortfolioAnalysis()
  if (!portfolioAnalysis.value) {
    await refreshPortfolioAnalysis()
  }
}

function goToFund(code) {
  router.push(`/fund/${code}`)
}

onMounted(async () => {
  await Promise.all([
    fundStore.loadFunds(),
    holdingStore.loadHoldingsSummary(),
    aiStore.loadAISettings(),
    holdingStore.loadRecentTrades(10),
    loadIndices(),
    loadPortfolioHistory()
  ])
})
</script>

<template>
  <div class="home-page">
    <div class="action-bar">
      <el-button type="primary" @click="syncAllFunds" :loading="syncingAll">
        <el-icon><Refresh /></el-icon>
        同步净值
      </el-button>
      <el-tooltip content="同步所有基金的最新净值数据" placement="top">
        <el-icon class="help-icon"><QuestionFilled /></el-icon>
      </el-tooltip>
    </div>

    <DashboardStats
      :total-cost="holdingStore.holdingsSummary.total_cost"
      :total-market-value="holdingStore.holdingsSummary.total_market_value"
      :today-profit="holdingStore.holdingsSummary.today_profit"
      :total-profit="holdingStore.holdingsSummary.total_profit"
      :profit-rate="holdingStore.holdingsSummary.profit_rate"
      :position-info="positionInfo"
    />

    <el-row :gutter="24">
      <MarketIndices
        :indices="indicesData"
        :indices-loading="indicesLoading"
        :indices-date="indicesDate"
        :indices-is-today="indicesIsToday"
        :indices-update-time="indicesUpdateTime"
        @refresh="refreshIndices"
      />

      <PortfolioDistributionChart
        :holdings="holdingStore.holdingFunds"
      />

      <PortfolioHistoryChart
        :history="portfolioHistory"
        :loading="portfolioHistoryLoading"
      />

      <HoldingsTable
        :holdings="holdingStore.holdingFunds"
        @click-fund="goToFund"
      />

      <RecentTrades
        :trades="holdingStore.recentTrades"
        @click-fund="goToFund"
      />

      <ChangeRanking
        :holdings="holdingStore.holdingFunds"
        @click-fund="goToFund"
      />
    </el-row>

    <AIAnalysisDialog
      v-model="showAnalysisDialog"
      :loading="portfolioLoading"
      :analysis="portfolioAnalysis"
      @refresh="refreshPortfolioAnalysis"
    />
  </div>
</template>

<style scoped>
.home-page {
  width: 100%;
  max-width: 1400px;
}

.action-bar {
  margin-bottom: 24px;
  display: flex;
  justify-content: flex-end;
}

.action-bar .el-button--primary {
  background: #1890ff;
  border: none;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2);
  transition: all 0.3s;
  font-weight: 500;
}

.action-bar .el-button--primary:hover {
  background: #40a9ff;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
  transform: translateY(-1px);
}

.action-bar .el-button--primary:active {
  transform: translateY(0);
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
  transition: background 0.2s;
}

::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

* {
  scrollbar-width: thin;
  scrollbar-color: #d1d5db transparent;
}

.el-scrollbar__bar {
  opacity: 0.3;
  transition: opacity 0.3s;
}

.el-scrollbar__bar.is-horizontal {
  height: 6px;
}

.el-scrollbar__bar.is-vertical {
  width: 6px;
}

.el-scrollbar:hover .el-scrollbar__bar {
  opacity: 0.6;
}

.el-scrollbar__thumb {
  background-color: #9ca3af;
  border-radius: 3px;
}

.skeleton-container {
  padding: 20px 0;
}

.skeleton-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  align-items: center;
}

.skeleton-item {
  background: linear-gradient(90deg, #f0f2f5 25%, #e8e8e8 50%, #f0f2f5 75%);
  background-size: 200% 100%;
  border-radius: 6px;
  animation: skeleton-loading 1.5s ease-in-out infinite;
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border-radius: 16px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f0f0f0;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  gap: 12px;
  color: #909399;
}
</style>
