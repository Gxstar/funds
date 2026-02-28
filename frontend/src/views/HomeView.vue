<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/funds'
import { aiAPI } from '@/api'
import * as echarts from 'echarts'
import { marked } from 'marked'

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true
})

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

// 渲染 Markdown
function renderMarkdown(text) {
  if (!text) return ''
  return marked(text)
}

onMounted(async () => {
  await Promise.all([
    fundStore.loadFunds(),
    fundStore.loadHoldingsSummary(),
    fundStore.loadAISettings()
  ])
  
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
    <!-- 顶部统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
          <el-icon><Wallet /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">总投入</div>
          <div class="stat-value">{{ formatCurrency(fundStore.holdingsSummary.total_cost) }}</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">总市值</div>
          <div class="stat-value">{{ formatCurrency(fundStore.holdingsSummary.total_market_value) }}</div>
        </div>
      </div>
      
      <div class="stat-card highlight" :class="{ profit: fundStore.holdingsSummary.total_profit > 0, loss: fundStore.holdingsSummary.total_profit < 0 }">
        <div class="stat-icon">
          <el-icon><DataLine /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">总盈亏</div>
          <div class="stat-value">
            {{ formatCurrency(fundStore.holdingsSummary.total_profit) }}
            <span class="stat-sub">{{ formatPercent(fundStore.holdingsSummary.profit_rate) }}</span>
          </div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
          <el-icon><PieChart /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">当前仓位</div>
          <div class="stat-value" v-if="positionInfo">{{ positionInfo.ratio }}%</div>
          <div class="stat-value" v-else>-</div>
          <div class="stat-hint" v-if="positionInfo">剩余 {{ formatCurrency(positionInfo.available) }}</div>
          <div class="stat-hint" v-else>未设置满仓金额</div>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-bar">
      <el-button type="primary" size="large" @click="analyzePortfolio" :loading="portfolioLoading">
        <el-icon><MagicStick /></el-icon>
        AI 持仓分析
      </el-button>
    </div>

    <!-- 数据卡片 -->
    <el-row :gutter="20">
      <!-- 持仓分布 -->
      <el-col :span="12">
        <div class="data-card">
          <div class="card-header">
            <span class="title">持仓分布</span>
          </div>
          <div class="card-body">
            <div ref="pieChart" class="chart-container"></div>
          </div>
        </div>
      </el-col>
      
      <!-- 今日涨跌 -->
      <el-col :span="12">
        <div class="data-card">
          <div class="card-header">
            <span class="title">今日涨跌</span>
            <el-tag size="small" type="info">{{ sortedHoldings.length }} 只</el-tag>
          </div>
          <div class="card-body">
            <el-scrollbar height="240px">
              <div class="list-container">
                <div
                  v-for="fund in sortedHoldings"
                  :key="fund.fund_code"
                  class="change-item"
                  @click="goToFund(fund.fund_code)"
                >
                  <div class="item-left">
                    <span class="name">{{ fund.fund_name }}</span>
                    <span class="code">{{ fund.fund_code }}</span>
                  </div>
                  <div class="item-right">
                    <span class="change" :class="{ positive: fund.last_growth_rate > 0, negative: fund.last_growth_rate < 0 }">
                      {{ fund.last_growth_rate ? (fund.last_growth_rate > 0 ? '+' : '') + fund.last_growth_rate.toFixed(2) + '%' : '-' }}
                    </span>
                  </div>
                </div>
                <el-empty v-if="sortedHoldings.length === 0" description="暂无持仓" :image-size="60" />
              </div>
            </el-scrollbar>
          </div>
        </div>
      </el-col>
      
      <!-- 持仓明细 -->
      <el-col :span="12">
        <div class="data-card">
          <div class="card-header">
            <span class="title">持仓明细</span>
            <el-tag size="small" type="info">{{ fundStore.hasHoldingFunds.length }} 只</el-tag>
          </div>
          <div class="card-body">
            <el-scrollbar height="280px">
              <div class="list-container">
                <div
                  v-for="fund in fundStore.hasHoldingFunds"
                  :key="fund.fund_code"
                  class="holding-item"
                  @click="goToFund(fund.fund_code)"
                >
                  <div class="item-left">
                    <span class="name">{{ fund.fund_name }}</span>
                    <span class="code">{{ fund.fund_code }}</span>
                  </div>
                  <div class="item-right">
                    <div class="market-value">{{ formatCurrency(parseFloat(fund.total_shares) * parseFloat(fund.last_net_value || 0)) }}</div>
                    <div class="profit" :class="{ positive: fund.last_growth_rate > 0, negative: fund.last_growth_rate < 0 }">
                      {{ formatCurrency(parseFloat(fund.total_shares) * parseFloat(fund.last_net_value || 0) - parseFloat(fund.total_cost || 0)) }}
                    </div>
                  </div>
                </div>
                <el-empty v-if="fundStore.hasHoldingFunds.length === 0" description="暂无持仓" :image-size="60" />
              </div>
            </el-scrollbar>
          </div>
        </div>
      </el-col>
      
      <!-- 近期交易 -->
      <el-col :span="12">
        <div class="data-card">
          <div class="card-header">
            <span class="title">近期交易</span>
          </div>
          <div class="card-body">
            <el-scrollbar height="280px">
              <div class="list-container">
                <div
                  v-for="trade in fundStore.recentTrades"
                  :key="trade.id"
                  class="trade-item"
                  @click="goToFund(trade.fund_code)"
                >
                  <div class="item-left">
                    <span class="name">{{ trade.fund_name }}</span>
                    <span class="code">{{ trade.trade_date }} · {{ trade.trade_type === 'BUY' ? '买入' : '卖出' }}</span>
                  </div>
                  <div class="item-right">
                    <span class="amount" :class="{ buy: trade.trade_type === 'BUY', sell: trade.trade_type === 'SELL' }">
                      {{ trade.trade_type === 'BUY' ? '-' : '+' }}{{ formatCurrency(trade.amount) }}
                    </span>
                  </div>
                </div>
                <el-empty v-if="fundStore.recentTrades.length === 0" description="暂无交易记录" :image-size="60" />
              </div>
            </el-scrollbar>
          </div>
        </div>
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
        <div class="analysis-summary">
          <div class="summary-item">
            <div class="summary-label">持有基金</div>
            <div class="summary-value">{{ portfolioAnalysis.summary?.fund_count }} 只</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">总投入</div>
            <div class="summary-value">{{ formatCurrency(portfolioAnalysis.summary?.total_cost) }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">总市值</div>
            <div class="summary-value">{{ formatCurrency(portfolioAnalysis.summary?.total_market_value) }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">总盈亏</div>
            <div class="summary-value" :class="{ positive: portfolioAnalysis.summary?.total_profit > 0, negative: portfolioAnalysis.summary?.total_profit < 0 }">
              {{ formatCurrency(portfolioAnalysis.summary?.total_profit) }}
            </div>
          </div>
          <div class="summary-item">
            <div class="summary-label">收益率</div>
            <div class="summary-value" :class="{ positive: portfolioAnalysis.summary?.profit_rate > 0, negative: portfolioAnalysis.summary?.profit_rate < 0 }">
              {{ formatPercent(portfolioAnalysis.summary?.profit_rate) }}
            </div>
          </div>
          <div class="summary-item">
            <div class="summary-label">账户仓位</div>
            <div class="summary-value">{{ portfolioAnalysis.summary?.position_ratio?.toFixed(1) }}%</div>
          </div>
        </div>
        <!-- 分析内容 -->
        <el-scrollbar height="400px" class="analysis-content">
          <div class="markdown-body" v-html="renderMarkdown(portfolioAnalysis.analysis)"></div>
        </el-scrollbar>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.home-page {
  max-width: 1400px;
}

/* 统计卡片 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 22px;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
}

.stat-sub {
  font-size: 14px;
  font-weight: 500;
  display: block;
  margin-top: 2px;
}

.stat-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.stat-card.highlight {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.stat-card.highlight .stat-label,
.stat-card.highlight .stat-hint {
  color: rgba(255, 255, 255, 0.8);
}

.stat-card.highlight .stat-value {
  color: #fff;
}

.stat-card.highlight .stat-icon {
  background: rgba(255, 255, 255, 0.2);
}

.stat-card.highlight.profit .stat-sub {
  color: #ff9999;
}

.stat-card.highlight.loss .stat-sub {
  color: #99ffcc;
}

/* 操作按钮 */
.action-bar {
  margin-bottom: 20px;
  display: flex;
  justify-content: flex-end;
}

/* 数据卡片 */
.data-card {
  background: #fff;
  border-radius: 12px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.card-header .title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.card-body {
  padding: 16px 20px;
}

.chart-container {
  width: 100%;
  height: 240px;
}

/* 列表容器 */
.list-container {
  margin: -4px 0;
}

/* 涨跌项 */
.change-item, .holding-item, .trade-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.2s;
}

.change-item:last-child, .holding-item:last-child, .trade-item:last-child {
  border-bottom: none;
}

.change-item:hover, .holding-item:hover, .trade-item:hover {
  background: #fafafa;
  margin: 0 -20px;
  padding: 12px 20px;
}

.item-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.item-left .name {
  font-weight: 500;
  font-size: 14px;
  color: #1a1a2e;
}

.item-left .code {
  font-size: 12px;
  color: #909399;
}

.item-right {
  text-align: right;
}

.change {
  font-size: 15px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 6px;
}

.change.positive {
  color: #f56c6c;
  background: #fef0f0;
}

.change.negative {
  color: #67c23a;
  background: #f0f9eb;
}

.holding-item .market-value {
  font-weight: 600;
  font-size: 14px;
  color: #1a1a2e;
}

.holding-item .profit {
  font-size: 12px;
  margin-top: 2px;
}

.amount.buy {
  color: #f56c6c;
  font-weight: 600;
}

.amount.sell {
  color: #67c23a;
  font-weight: 600;
}

/* 加载 */
.loading-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  gap: 12px;
  color: #909399;
}

/* 分析汇总 */
.analysis-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
}

.analysis-summary .summary-item {
  text-align: center;
}

.analysis-summary .summary-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.analysis-summary .summary-value {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
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
