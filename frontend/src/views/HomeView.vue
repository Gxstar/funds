<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/funds'
import { aiAPI } from '@/api'
import * as echarts from 'echarts'

const router = useRouter()
const fundStore = useFundStore()

const portfolioLoading = ref(false)
const portfolioAnalysis = ref(null)
const pieChart = ref(null)
let chartInstance = null

// 格式化
function formatCurrency(value) {
  if (value === null || value === undefined) return '¥0.00'
  return '¥' + parseFloat(value).toLocaleString('zh-CN', { minimumFractionDigits: 2 })
}

function formatPercent(value) {
  if (value === null || value === undefined) return '0.00%'
  const num = parseFloat(value)
  return (num > 0 ? '+' : '') + num.toFixed(2) + '%'
}

// 仓位信息
const positionInfo = computed(() => {
  const total = parseFloat(fundStore.aiSettings?.total_position_amount) || 0
  const market = fundStore.holdingsSummary.total_market_value
  if (total > 0) {
    const ratio = (market / total * 100).toFixed(1)
    const available = total - market
    return { ratio, available, total }
  }
  return null
})

// 持仓基金（按涨跌幅排序）
const sortedHoldings = computed(() => {
  return [...fundStore.hasHoldingFunds].sort((a, b) => 
    (b.last_growth_rate || 0) - (a.last_growth_rate || 0)
  )
})

// 分析弹窗显示控制
const showAnalysisDialog = computed({
  get: () => portfolioLoading.value || !!portfolioAnalysis.value,
  set: (val) => { if (!val) portfolioAnalysis.value = null }
})

// 初始化饼图
function initPieChart() {
  if (!pieChart.value) return
  
  chartInstance = echarts.init(pieChart.value)
  
  const holdings = fundStore.hasHoldingFunds
  if (holdings.length === 0) {
    chartInstance.setOption({
      title: { text: '暂无持仓', left: 'center', top: 'center', textStyle: { color: '#909399' } }
    })
    return
  }
  
  const data = holdings.map(f => ({
    name: f.fund_name || f.fund_code,
    value: Math.round(parseFloat(f.total_shares) * parseFloat(f.last_net_value || 0))
  }))
  
  chartInstance.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { orient: 'vertical', right: 10, top: 'center', itemWidth: 10, itemHeight: 10 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
      data
    }]
  })
}

// AI 持仓分析
async function analyzePortfolio() {
  portfolioLoading.value = true
  try {
    const result = await aiAPI.analyze()
    if (result.error) throw new Error(result.error)
    portfolioAnalysis.value = result
  } catch (error) {
    ElMessage.error(error.message || '分析失败')
  } finally {
    portfolioLoading.value = false
  }
}

// 跳转基金详情
function goToFund(code) {
  router.push(`/fund/${code}`)
}

onMounted(async () => {
  await fundStore.loadFunds()
  await fundStore.loadHoldingsSummary()
  
  // 需要在数据加载后初始化图表
  setTimeout(initPieChart, 100)
  
  window.addEventListener('resize', () => chartInstance?.resize())
})

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', () => chartInstance?.resize())
})
</script>

<template>
  <div class="home-page">
    <!-- 资产概览 -->
    <el-row :gutter="20" class="summary-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="summary-item">
            <div class="label">总投入</div>
            <div class="value">{{ formatCurrency(fundStore.holdingsSummary.total_cost) }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="summary-item">
            <div class="label">总市值</div>
            <div class="value">{{ formatCurrency(fundStore.holdingsSummary.total_market_value) }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="highlight-card">
          <div class="summary-item">
            <div class="label">总盈亏</div>
            <div class="value">
              {{ formatCurrency(fundStore.holdingsSummary.total_profit) }}
              <span class="sub">{{ formatPercent(fundStore.holdingsSummary.profit_rate) }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="summary-item">
            <div class="label">当前仓位</div>
            <div class="value" v-if="positionInfo">{{ positionInfo.ratio }}%</div>
            <div class="value" v-else>-</div>
            <div class="hint" v-if="positionInfo">剩余 {{ formatCurrency(positionInfo.available) }}</div>
            <div class="hint" v-else>未设置满仓金额</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 操作按钮 -->
    <div class="action-bar">
      <el-button type="primary" @click="analyzePortfolio" :loading="portfolioLoading">
        <el-icon><MagicStick /></el-icon>
        AI 持仓分析
      </el-button>
    </div>

    <!-- 数据卡片 -->
    <el-row :gutter="20">
      <!-- 持仓分布 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>持仓分布</template>
          <div ref="pieChart" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <!-- 今日涨跌 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>今日涨跌</template>
          <el-scrollbar height="250px">
            <div
              v-for="fund in sortedHoldings"
              :key="fund.fund_code"
              class="change-item"
              @click="goToFund(fund.fund_code)"
            >
              <div>
                <span class="name">{{ fund.fund_name }}</span>
                <el-tag size="small" type="info">{{ fund.fund_code }}</el-tag>
              </div>
              <div class="change-wrapper">
                <span class="date">{{ fund.last_price_date }}</span>
                <span
                  class="change"
                  :class="{ positive: fund.last_growth_rate > 0, negative: fund.last_growth_rate < 0 }"
                >
                  {{ fund.last_growth_rate ? (fund.last_growth_rate > 0 ? '+' : '') + fund.last_growth_rate.toFixed(2) + '%' : '-' }}
                </span>
              </div>
            </div>
            <el-empty v-if="sortedHoldings.length === 0" description="暂无持仓" :image-size="60" />
          </el-scrollbar>
        </el-card>
      </el-col>
      
      <!-- 持仓明细 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>持仓基金</template>
          <el-scrollbar height="300px">
            <div
              v-for="fund in fundStore.hasHoldingFunds"
              :key="fund.fund_code"
              class="holding-item"
              @click="goToFund(fund.fund_code)"
            >
              <div>
                <div class="name">{{ fund.fund_name }}</div>
                <el-tag size="small" type="info">{{ fund.fund_code }}</el-tag>
              </div>
              <div class="holding-info">
                <div class="market-value">
                  {{ formatCurrency(parseFloat(fund.total_shares) * parseFloat(fund.last_net_value || 0)) }}
                </div>
                <div class="profit" :class="{ positive: fund.last_growth_rate > 0, negative: fund.last_growth_rate < 0 }">
                  {{ formatCurrency(parseFloat(fund.total_shares) * parseFloat(fund.last_net_value || 0) - parseFloat(fund.total_cost || 0)) }}
                </div>
              </div>
            </div>
            <el-empty v-if="fundStore.hasHoldingFunds.length === 0" description="暂无持仓" :image-size="60" />
          </el-scrollbar>
        </el-card>
      </el-col>
      
      <!-- 近期交易 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>近期交易</template>
          <el-scrollbar height="300px">
            <div
              v-for="trade in fundStore.recentTrades"
              :key="trade.id"
              class="trade-item"
              @click="goToFund(trade.fund_code)"
            >
              <div>
                <div class="name">{{ trade.fund_name }}</div>
                <div class="info">{{ trade.trade_date }} · {{ trade.trade_type === 'BUY' ? '买入' : '卖出' }}</div>
              </div>
              <div class="amount" :class="{ buy: trade.trade_type === 'BUY', sell: trade.trade_type === 'SELL' }">
                {{ trade.trade_type === 'BUY' ? '-' : '+' }}{{ formatCurrency(trade.amount) }}
              </div>
            </div>
            <el-empty v-if="fundStore.recentTrades.length === 0" description="暂无交易记录" :image-size="60" />
          </el-scrollbar>
        </el-card>
      </el-col>
    </el-row>

    <!-- AI 分析结果弹窗 -->
    <el-dialog v-model="showAnalysisDialog" title="AI 持仓分析报告" width="700px">
      <div v-if="portfolioLoading" class="loading-wrapper">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <span>正在分析您的持仓组合...</span>
      </div>
      <div v-else-if="portfolioAnalysis">
        <!-- 汇总 -->
        <el-descriptions :column="3" border class="portfolio-summary">
          <el-descriptions-item label="持有基金">{{ portfolioAnalysis.summary?.fund_count }} 只</el-descriptions-item>
          <el-descriptions-item label="总投入">{{ formatCurrency(portfolioAnalysis.summary?.total_cost) }}</el-descriptions-item>
          <el-descriptions-item label="总市值">{{ formatCurrency(portfolioAnalysis.summary?.total_market_value) }}</el-descriptions-item>
          <el-descriptions-item label="总盈亏">
            <span :class="{ positive: portfolioAnalysis.summary?.total_profit > 0, negative: portfolioAnalysis.summary?.total_profit < 0 }">
              {{ formatCurrency(portfolioAnalysis.summary?.total_profit) }} ({{ formatPercent(portfolioAnalysis.summary?.profit_rate) }})
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="账户仓位">{{ portfolioAnalysis.summary?.position_ratio?.toFixed(1) }}%</el-descriptions-item>
        </el-descriptions>
        <!-- 分析内容 -->
        <el-scrollbar height="400px" class="analysis-content">
          <div class="markdown-body" v-html="portfolioAnalysis.analysis"></div>
        </el-scrollbar>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.home-page {
  max-width: 1400px;
}

.summary-row {
  margin-bottom: 20px;
}

.summary-item {
  text-align: center;
}

.summary-item .label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.summary-item .value {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
}

.summary-item .sub {
  font-size: 14px;
  font-weight: 500;
  display: block;
  margin-top: 4px;
}

.summary-item .hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.highlight-card {
  background: linear-gradient(135deg, #4f7cff 0%, #7c3aed 100%);
}

.highlight-card :deep(.el-card__body) {
  color: #fff;
}

.highlight-card .label,
.highlight-card .hint {
  color: rgba(255, 255, 255, 0.8);
}

.highlight-card .value {
  color: #fff;
}

.action-bar {
  margin-bottom: 20px;
  display: flex;
  justify-content: flex-end;
}

.chart-container {
  width: 100%;
  height: 250px;
}

.change-item, .holding-item, .trade-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
}

.change-item:hover, .holding-item:hover, .trade-item:hover {
  background: #f5f7fa;
  margin: 0 -20px;
  padding: 10px 20px;
}

.change-item .name, .holding-item .name, .trade-item .name {
  font-weight: 500;
}

.change-item .date {
  font-size: 12px;
  color: #909399;
  margin-right: 8px;
}

.change-wrapper {
  display: flex;
  align-items: center;
}

.change {
  font-weight: 600;
}

.change.positive, .profit.positive {
  color: #f56c6c;
}

.change.negative, .profit.negative {
  color: #67c23a;
}

.holding-info {
  text-align: right;
}

.holding-info .profit {
  font-size: 12px;
}

.amount.buy {
  color: #f56c6c;
}

.amount.sell {
  color: #67c23a;
}

.trade-item .info {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.loading-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  gap: 12px;
  color: #909399;
}

.portfolio-summary {
  margin-bottom: 20px;
}

.analysis-content {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
}

.markdown-body {
  line-height: 1.8;
}

.positive {
  color: #f56c6c;
}

.negative {
  color: #67c23a;
}
</style>
