<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/funds'
import { aiAPI, marketAPI } from '@/api'
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

// 市场指数数据
const indicesData = ref([])
const indicesLoading = ref(false)
const indicesDate = ref('')
const indicesIsToday = ref(true)

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

// 持仓基金（按市值排序）
const sortedHoldings = computed(() => {
  return [...fundStore.hasHoldingFunds].sort((a, b) => {
    const valueA = parseFloat(a.total_shares || 0) * parseFloat(a.last_net_value || 0)
    const valueB = parseFloat(b.total_shares || 0) * parseFloat(b.last_net_value || 0)
    return valueB - valueA
  })
})

// 涨跌统计
const changeStats = computed(() => {
  const funds = fundStore.hasHoldingFunds
  let up = 0, down = 0, flat = 0
  let totalChange = 0
  
  funds.forEach(f => {
    const rate = f.last_growth_rate
    if (rate === null || rate === undefined) {
      flat++
    } else if (parseFloat(rate) > 0) {
      up++
      totalChange += parseFloat(rate)
    } else if (parseFloat(rate) < 0) {
      down++
      totalChange += parseFloat(rate)
    } else {
      flat++
    }
  })
  
  return {
    total: funds.length,
    up,
    down,
    flat,
    avgChange: funds.length > 0 ? (totalChange / funds.length).toFixed(2) : 0
  }
})

// 分析弹窗显示控制
const showAnalysisDialog = computed({
  get: () => portfolioLoading.value || !!portfolioAnalysis.value,
  set: (val) => { if (!val) portfolioAnalysis.value = null }
})

// 图表类型切换
const chartType = ref('pie') // 'pie' 或 'treemap'

// 切换图表类型
function toggleChartType() {
  chartType.value = chartType.value === 'pie' ? 'treemap' : 'pie'
  updateChart()
}

// 初始化图表
function initPieChart() {
  if (!pieChart.value) return
  
  chartInstance = echarts.init(pieChart.value)
  updateChart()
}

// 更新图表
function updateChart() {
  if (!chartInstance) return
  
  const holdings = fundStore.hasHoldingFunds
  if (holdings.length === 0) {
    chartInstance.setOption({
      title: { text: '暂无持仓', left: 'center', top: 'center', textStyle: { color: '#909399' } }
    }, true)
    return
  }
  
  const data = holdings.map(f => ({
    name: f.fund_name || f.fund_code,
    value: Math.round(parseFloat(f.total_shares) * parseFloat(f.last_net_value || 0))
  }))
  
  if (chartType.value === 'pie') {
    chartInstance.setOption({
      title: { show: false },
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
    }, true)
  } else {
    // 矩形树图
    chartInstance.setOption({
      title: { show: false },
      tooltip: { trigger: 'item', formatter: '{b}: ¥{c}' },
      legend: { show: false },
      series: [{
        type: 'treemap',
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        label: { show: true, fontSize: 11, overflow: 'truncate', ellipsis: '...' },
        upperLabel: { show: true, height: 20 },
        itemStyle: { borderRadius: 4, gapWidth: 2, borderColor: '#fff', borderWidth: 2 },
        emphasis: { focus: 'descendant' },
        levels: [
          {
            itemStyle: { borderWidth: 2, gapWidth: 2 }
          }
        ],
        data
      }]
    }, true)
  }
}

// 加载市场指数
async function loadIndices() {
  indicesLoading.value = true
  try {
    const result = await marketAPI.getIndices()
    indicesData.value = result.data || []
    indicesDate.value = result.date || ''
    indicesIsToday.value = result.is_today !== false
  } catch (error) {
    console.error('加载市场指数失败:', error)
  } finally {
    indicesLoading.value = false
  }
}

// 格式化指数日期显示
function formatIndicesDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const month = d.getMonth() + 1
  const day = d.getDate()
  return `${month}月${day}日`
}

// 格式化分析时间显示
function formatAnalysisTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const year = d.getFullYear()
  const month = d.getMonth() + 1
  const day = d.getDate()
  const hour = d.getHours().toString().padStart(2, '0')
  const minute = d.getMinutes().toString().padStart(2, '0')
  return `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')} ${hour}:${minute}`
}

// AI 持仓分析 - 加载缓存（优先展示缓存，没有缓存不弹窗）
async function loadPortfolioAnalysis() {
  portfolioLoading.value = true
  try {
    // cacheOnly=true：只获取缓存，没有缓存时返回 no_cache
    const result = await aiAPI.analyze(false, true)
    if (result.no_cache) {
      // 没有缓存，不显示弹窗
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

// AI 持仓分析 - 刷新分析（强制重新分析并更新数据库）
async function refreshPortfolioAnalysis() {
  portfolioLoading.value = true
  try {
    // forceRefresh=true：强制重新分析，结果会保存到数据库替换旧数据
    const result = await aiAPI.analyze(true, false)
    if (result.error) throw new Error(result.error)
    portfolioAnalysis.value = result
  } catch (error) {
    ElMessage.error(error.message || '分析失败')
  } finally {
    portfolioLoading.value = false
  }
}

// AI 持仓分析 - 打开弹窗
async function openAnalysisDialog() {
  // 先尝试加载缓存
  await loadPortfolioAnalysis()
  // 如果没有缓存，则进行新分析
  if (!portfolioAnalysis.value) {
    await refreshPortfolioAnalysis()
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
    fundStore.loadAISettings(),
    fundStore.loadRecentTrades(10),
    loadIndices()
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
      <el-button type="primary" size="large" @click="openAnalysisDialog" :loading="portfolioLoading">
        <el-icon><MagicStick /></el-icon>
        AI 持仓分析
      </el-button>
    </div>

    <!-- 数据卡片 -->
    <el-row :gutter="20">
      <!-- 市场概况 -->
      <el-col :span="12">
        <div class="data-card">
          <div class="card-header">
            <span class="title">市场概况</span>
            <el-tag size="small" :type="indicesIsToday ? 'success' : 'info'" v-if="indicesData.length">
              {{ indicesIsToday ? '今日' : formatIndicesDate(indicesDate) }}
            </el-tag>
          </div>
          <div class="card-body">
            <div class="indices-grid" v-loading="indicesLoading">
              <div 
                v-for="index in indicesData" 
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
              <el-empty v-if="!indicesLoading && indicesData.length === 0" description="暂无数据" :image-size="60" />
            </div>
          </div>
        </div>
      </el-col>
      
      <!-- 持仓分布 -->
      <el-col :span="12">
        <div class="data-card">
          <div class="card-header">
            <span class="title">持仓分布</span>
            <el-button-group size="small">
              <el-button 
                :type="chartType === 'pie' ? 'primary' : ''" 
                @click="chartType = 'pie'; updateChart()"
              >
                <el-icon><PieChart /></el-icon>
              </el-button>
              <el-button 
                :type="chartType === 'treemap' ? 'primary' : ''" 
                @click="chartType = 'treemap'; updateChart()"
              >
                <el-icon><Grid /></el-icon>
              </el-button>
            </el-button-group>
          </div>
          <div class="card-body">
            <div ref="pieChart" class="chart-container"></div>
          </div>
        </div>
      </el-col>
      
      <!-- 我的持仓（合并涨跌和明细） -->
      <el-col :span="12">
        <div class="data-card">
          <div class="card-header">
            <span class="title">我的持仓</span>
            <div class="header-stats">
              <el-tag size="small" type="danger" v-if="changeStats.up > 0">{{ changeStats.up }} 涨</el-tag>
              <el-tag size="small" type="success" v-if="changeStats.down > 0">{{ changeStats.down }} 跌</el-tag>
              <el-tag size="small" type="info">{{ changeStats.total }} 只</el-tag>
            </div>
          </div>
          <div class="card-body">
            <el-scrollbar height="280px">
              <div class="list-container">
                <div
                  v-for="fund in sortedHoldings"
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
                    <div class="detail-row">
                      <span class="profit" :class="{ positive: fund.total_cost && (parseFloat(fund.total_shares) * parseFloat(fund.last_net_value || 0) - parseFloat(fund.total_cost)) > 0, negative: fund.total_cost && (parseFloat(fund.total_shares) * parseFloat(fund.last_net_value || 0) - parseFloat(fund.total_cost)) < 0 }">
                        {{ formatCurrency(parseFloat(fund.total_shares) * parseFloat(fund.last_net_value || 0) - parseFloat(fund.total_cost || 0)) }}
                      </span>
                      <span class="today-change" :class="{ positive: fund.last_growth_rate > 0, negative: fund.last_growth_rate < 0 }">
                        {{ fund.last_growth_rate ? (fund.last_growth_rate > 0 ? '+' : '') + fund.last_growth_rate.toFixed(2) + '%' : '-' }}
                      </span>
                    </div>
                  </div>
                </div>
                <el-empty v-if="sortedHoldings.length === 0" description="暂无持仓" :image-size="60" />
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
        <!-- 分析时间和缓存状态 -->
        <div class="analysis-header">
          <div class="analysis-time">
            <el-icon><Clock /></el-icon>
            <span>分析时间：{{ formatAnalysisTime(portfolioAnalysis.timestamp) }}</span>
          </div>
          <div class="analysis-actions">
            <el-tag v-if="portfolioAnalysis.cached" type="warning" size="small">缓存</el-tag>
            <el-tag v-else type="success" size="small">最新</el-tag>
            <el-button type="primary" size="small" @click="refreshPortfolioAnalysis" :loading="portfolioLoading">
              <el-icon><Refresh /></el-icon>
              刷新分析
            </el-button>
          </div>
        </div>
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

.card-header .header-stats {
  display: flex;
  gap: 6px;
}

.card-body {
  padding: 16px 20px;
}

.chart-container {
  width: 100%;
  height: 240px;
  overflow: hidden;
}

/* 市场指数 */
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
  background: #f5f7fa;
  border-radius: 8px;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.index-item.up {
  background: #fef0f0;
}

.index-item.down {
  background: #f0f9eb;
}

.index-name {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.index-price {
  font-size: 16px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.index-change {
  font-size: 12px;
  color: #909399;
}

.index-item.up .index-price,
.index-item.up .index-change {
  color: #f56c6c;
}

.index-item.down .index-price,
.index-item.down .index-change {
  color: #67c23a;
}

.change-pct {
  margin-left: 4px;
  font-weight: 600;
}

/* 列表容器 */
.list-container {
  margin: -4px 0;
}

/* 持仓项 */
.holding-item, .trade-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.2s;
}

.holding-item:last-child, .trade-item:last-child {
  border-bottom: none;
}

.holding-item:hover, .trade-item:hover {
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

.holding-item .market-value {
  font-weight: 600;
  font-size: 14px;
  color: #1a1a2e;
}

.holding-item .detail-row {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 2px;
}

.holding-item .profit {
  font-size: 12px;
}

.today-change {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
}

.today-change.positive {
  color: #f56c6c;
  background: #fef0f0;
}

.today-change.negative {
  color: #67c23a;
  background: #f0f9eb;
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

/* 分析头部 */
.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.analysis-time {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.analysis-actions {
  display: flex;
  align-items: center;
  gap: 10px;
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