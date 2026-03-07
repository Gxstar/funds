<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/funds'
import { aiAPI, marketAPI, holdingAPI } from '@/api'
import { formatCurrency, formatPercent, formatDate, formatDateTime } from '@/utils/format'
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

// 历史收益图表
const portfolioHistoryChart = ref(null)
let historyChartInstance = null
const portfolioHistory = ref({
  dates: [],
  market_values: [],
  costs: [],
  profits: [],
  profit_rates: []
})
const portfolioHistoryLoading = ref(false)

// 市场指数数据
const indicesData = ref([])
const indicesLoading = ref(false)
const indicesDate = ref('')
const indicesIsToday = ref(true)
const indicesUpdateTime = ref('')

// 指数选择对话框
const showIndicesDialog = ref(false)
const availableIndices = ref([])
const selectedIndicesCodes = ref([])
const indicesSaving = ref(false)

// 按类别分组的可选指数
const groupedIndices = computed(() => {
  const groups = { 'A股': [], '港股': [], '美股': [] }
  availableIndices.value.forEach(idx => {
    if (groups[idx.category]) {
      groups[idx.category].push(idx)
    }
  })
  return groups
})

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

// 涨跌排行类型切换：'daily' 当日涨跌，'hold' 持有收益
const changeRankType = ref('daily')

// 涨跌排行（取前3涨和前3跌）
const topChanges = computed(() => {
  const holdings = fundStore.hasHoldingFunds
  
  if (changeRankType.value === 'daily') {
    // 当日涨跌排行
    const funds = holdings
      .filter(f => f.last_growth_rate !== null && f.last_growth_rate !== undefined)
      .sort((a, b) => parseFloat(b.last_growth_rate) - parseFloat(a.last_growth_rate))
    
    return {
      topGainers: funds.slice(0, 3).map(f => ({
        ...f,
        displayRate: f.last_growth_rate,
        isDaily: true
      })),
      topLosers: funds.slice(-3).reverse().map(f => ({
        ...f,
        displayRate: f.last_growth_rate,
        isDaily: true
      }))
    }
  } else {
    // 持有收益排行
    const funds = holdings
      .filter(f => f.total_cost && parseFloat(f.total_cost) > 0 && f.last_net_value)
      .map(f => {
        const currentValue = parseFloat(f.total_shares || 0) * parseFloat(f.last_net_value || 0)
        const cost = parseFloat(f.total_cost || 0)
        const profitRate = cost > 0 ? ((currentValue - cost) / cost * 100) : 0
        return {
          ...f,
          displayRate: profitRate,
          isDaily: false
        }
      })
      .sort((a, b) => b.displayRate - a.displayRate)
    
    return {
      topGainers: funds.slice(0, 3),
      topLosers: funds.slice(-3).reverse()
    }
  }
})

// 分析弹窗显示控制
const showAnalysisDialog = computed({
  get: () => portfolioLoading.value || !!portfolioAnalysis.value,
  set: (val) => { if (!val) portfolioAnalysis.value = null }
})

// 图表类型切换
const chartType = ref('pie') // 'pie' 或 'rose'

// 切换图表类型
function toggleChartType() {
  chartType.value = chartType.value === 'pie' ? 'rose' : 'pie'
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
  
  // 统一的靛蓝色系配色
  const indigoColors = [
    '#6366f1', '#818cf8', '#a5b4fc', '#c7d2fe',
    '#4f46e5', '#6366f1', '#8b5cf6', '#a78bfa',
    '#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe'
  ]

  if (chartType.value === 'pie') {
    chartInstance.setOption({
      title: { show: false },
      tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
      legend: { 
        orient: 'vertical', 
        right: 5, 
        top: 'middle',
        itemWidth: 8, 
        itemHeight: 8,
        textStyle: { fontSize: 11 }
      },
      color: indigoColors,
      series: [{
        type: 'pie',
        radius: ['35%', '75%'],
        center: ['38%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold' } },
        data
      }]
    }, true)
  } else {
    // 南丁格尔玫瑰图
    chartInstance.setOption({
      title: { show: false },
      tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
      legend: { 
        orient: 'vertical', 
        right: 5, 
        top: 'middle',
        itemWidth: 8, 
        itemHeight: 8,
        textStyle: { fontSize: 11 }
      },
      color: indigoColors,
      series: [{
        type: 'pie',
        radius: [15, '72%'],
        center: ['38%', '50%'],
        roseType: 'radius',
        itemStyle: { borderRadius: 3, borderColor: '#fff', borderWidth: 1 },
        label: { show: false },
        emphasis: { 
          label: { show: true, fontSize: 12, fontWeight: 'bold' },
          itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.2)' }
        },
        data
      }]
    }, true)
  }
}

// 加载持仓历史收益
async function loadPortfolioHistory() {
  portfolioHistoryLoading.value = true
  try {
    const result = await holdingAPI.getPortfolioHistory(90)
    portfolioHistory.value = result
    initPortfolioHistoryChart()
  } catch (error) {
    console.error('加载持仓历史收益失败:', error)
  } finally {
    portfolioHistoryLoading.value = false
  }
}

// 初始化历史收益图表
function initPortfolioHistoryChart() {
  if (!portfolioHistoryChart.value) return
  
  if (historyChartInstance) {
    historyChartInstance.dispose()
  }
  
  historyChartInstance = echarts.init(portfolioHistoryChart.value)
  
  const { dates, profits, profit_rates } = portfolioHistory.value
  
  if (dates.length === 0) {
    historyChartInstance.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#909399' } }
    }, true)
    return
  }
  
  // 使用靛蓝色作为主色调，不区分盈亏
  const lineColor = '#6366f1'
  const areaColor = 'rgba(99, 102, 241, 0.15)'
  
  historyChartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line' },
      formatter: function(params) {
        const idx = params[0].dataIndex
        return `
          <div style="font-weight:600;margin-bottom:4px">${dates[idx]}</div>
          <div>累计收益: <span style="color:${profits[idx] >= 0 ? '#dc2626' : '#16a34a'};font-weight:600">${profits[idx] >= 0 ? '+' : ''}¥${profits[idx].toLocaleString()}</span></div>
          <div>收益率: <span style="color:${profit_rates[idx] >= 0 ? '#dc2626' : '#16a34a'};font-weight:600">${profit_rates[idx] >= 0 ? '+' : ''}${profit_rates[idx].toFixed(2)}%</span></div>
        `
      }
    },
    grid: {
      left: 10,
      right: 10,
      top: 10,
      bottom: 10,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { 
        show: true,
        fontSize: 10,
        color: '#909399',
        formatter: function(value) {
          const date = new Date(value)
          return `${date.getMonth() + 1}/${date.getDate()}`
        }
      }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { 
        lineStyle: { 
          type: 'dashed',
          color: '#f0f0f0'
        }
      },
      axisLabel: {
        fontSize: 10,
        color: '#909399',
        formatter: function(value) {
          if (Math.abs(value) >= 10000) {
            return (value / 10000).toFixed(1) + 'w'
          }
          return value
        }
      }
    },
    series: [{
      name: '累计收益',
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: {
        width: 2,
        color: lineColor
      },
      areaStyle: {
        color: areaColor
      },
      data: profits
    }]
  }, true)
}

// 加载市场指数
async function loadIndices(skipCache = false) {
  indicesLoading.value = true
  try {
    const result = await marketAPI.getIndices(skipCache)
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

// 刷新市场指数（强制获取最新数据）
async function refreshIndices() {
  await loadIndices(true)
}

// 打开指数选择对话框
async function openIndicesDialog() {
  showIndicesDialog.value = true
  // 加载可选指数和已选择的指数
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

// 保存指数选择
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
    // 重新加载指数数据
    await loadIndices()
  } catch (error) {
    console.error('保存指数选择失败:', error)
    ElMessage.error('保存失败')
  } finally {
    indicesSaving.value = false
  }
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
    loadIndices(),
    loadPortfolioHistory()
  ])
  
  // 需要在数据加载后初始化图表
  setTimeout(initPieChart, 100)
  
  window.addEventListener('resize', () => {
    chartInstance?.resize()
    historyChartInstance?.resize()
  })
})

onUnmounted(() => {
  chartInstance?.dispose()
  historyChartInstance?.dispose()
  window.removeEventListener('resize', () => {
    chartInstance?.resize()
    historyChartInstance?.resize()
  })
})
</script>

<template>
  <div class="home-page">
    <!-- 顶部统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);">
          <el-icon><Wallet /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">总投入</div>
          <div class="stat-value">{{ formatCurrency(fundStore.holdingsSummary.total_cost) }}</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #10b981 0%, #34d399 100%);">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">总市值</div>
          <div class="stat-value">{{ formatCurrency(fundStore.holdingsSummary.total_market_value) }}</div>
        </div>
      </div>
      
      <div class="stat-card highlight" :class="{ profit: fundStore.holdingsSummary.today_profit > 0, loss: fundStore.holdingsSummary.today_profit < 0 }">
        <div class="stat-icon">
          <el-icon><Sunrise /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">当日收益</div>
          <div class="stat-value">
            {{ (fundStore.holdingsSummary.today_profit > 0 ? '+' : '') + formatCurrency(fundStore.holdingsSummary.today_profit).slice(1) }}
          </div>
        </div>
      </div>
      
      <div class="stat-card" :class="{ profit: fundStore.holdingsSummary.total_profit > 0, loss: fundStore.holdingsSummary.total_profit < 0 }">
        <div class="stat-icon" style="background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);">
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
        <div class="stat-icon" style="background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);">
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

    <!-- 数据卡片 -->
    <el-row :gutter="24">
      <!-- 市场概况 -->
      <el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
        <div class="data-card">
          <div class="card-header">
            <span class="title">市场概况</span>
            <div class="header-actions">
              <span class="update-time" v-if="indicesUpdateTime">
                {{ formatDateTime(indicesUpdateTime) }}
              </span>
              <el-tag size="small" :type="indicesIsToday ? 'success' : 'info'" v-if="indicesData.length">
                {{ indicesIsToday ? '今日' : formatDate(indicesDate) }}
              </el-tag>
              <el-tooltip content="刷新数据" placement="top">
                <el-button size="small" circle @click="refreshIndices" :loading="indicesLoading">
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
      <el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
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
                :type="chartType === 'rose' ? 'primary' : ''" 
                @click="chartType = 'rose'; updateChart()"
              >
                <el-icon><Share /></el-icon>
              </el-button>
            </el-button-group>
          </div>
          <div class="card-body">
            <div ref="pieChart" class="chart-container"></div>
          </div>
        </div>
      </el-col>

      <!-- 历史收益 -->
      <el-col :span="12">
        <div class="data-card">
          <div class="card-header">
            <span class="title">历史收益</span>
            <div class="header-stats" v-if="portfolioHistory.profits.length > 0">
              <span class="history-summary" :class="{ profit: portfolioHistory.profits[portfolioHistory.profits.length - 1] >= 0, loss: portfolioHistory.profits[portfolioHistory.profits.length - 1] < 0 }">
                {{ portfolioHistory.profits[portfolioHistory.profits.length - 1] >= 0 ? '+' : '' }}{{ formatCurrency(portfolioHistory.profits[portfolioHistory.profits.length - 1]) }}
              </span>
            </div>
          </div>
          <div class="card-body">
            <div ref="portfolioHistoryChart" class="chart-container" v-loading="portfolioHistoryLoading"></div>
          </div>
        </div>
      </el-col>
      
      <!-- 我的持仓（合并涨跌和明细） -->
      <el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
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
            <el-scrollbar height="240px">
              <div class="list-container">
                <div
                  v-for="fund in sortedHoldings"
                  :key="fund.fund_code"
                  class="holding-item"
                  @click="goToFund(fund.fund_code)"
                >
                  <div class="item-left">
                    <span class="name">{{ fund.fund_name }}</span>
                    <div class="meta-row">
                      <span class="code">{{ fund.fund_code }}</span>
                      <span v-if="fund.last_price_date" class="price-date">{{ fund.last_price_date }}</span>
                    </div>
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
      <el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
        <div class="data-card">
          <div class="card-header">
            <span class="title">近期交易</span>
          </div>
          <div class="card-body">
            <el-scrollbar height="240px">
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

      <!-- 涨跌排行 -->
      <el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
        <div class="data-card">
          <div class="card-header">
            <span class="title">{{ changeRankType === 'daily' ? '涨跌排行' : '收益排行' }}</span>
            <el-button-group size="small">
              <el-button 
                :type="changeRankType === 'daily' ? 'primary' : ''" 
                @click="changeRankType = 'daily'"
              >
                当日
              </el-button>
              <el-button 
                :type="changeRankType === 'hold' ? 'primary' : ''" 
                @click="changeRankType = 'hold'"
              >
                持有
              </el-button>
            </el-button-group>
          </div>
          <div class="card-body">
            <div class="change-rank-container">
              <!-- 涨幅榜 -->
              <div class="rank-section">
                <div class="rank-title up">
                  <el-icon><Top /></el-icon>
                  <span>{{ changeRankType === 'daily' ? '涨幅前三' : '收益前三' }}</span>
                </div>
                <div class="rank-list">
                  <div
                    v-for="(fund, index) in topChanges.topGainers"
                    :key="fund.fund_code"
                    class="rank-item"
                    @click="goToFund(fund.fund_code)"
                  >
                    <span class="rank-num">{{ index + 1 }}</span>
                    <span class="rank-name">{{ fund.fund_name }}</span>
                    <span class="rank-rate" :class="{ up: fund.displayRate > 0, down: fund.displayRate < 0 }">
                      {{ fund.displayRate > 0 ? '+' : '' }}{{ fund.displayRate.toFixed(2) }}%
                    </span>
                  </div>
                  <el-empty v-if="topChanges.topGainers.length === 0" description="暂无数据" :image-size="40" />
                </div>
              </div>
              <!-- 跌幅榜 -->
              <div class="rank-section">
                <div class="rank-title down">
                  <el-icon><Bottom /></el-icon>
                  <span>{{ changeRankType === 'daily' ? '跌幅前三' : '亏损前三' }}</span>
                </div>
                <div class="rank-list">
                  <div
                    v-for="(fund, index) in topChanges.topLosers"
                    :key="fund.fund_code"
                    class="rank-item"
                    @click="goToFund(fund.fund_code)"
                  >
                    <span class="rank-num">{{ index + 1 }}</span>
                    <span class="rank-name">{{ fund.fund_name }}</span>
                    <span class="rank-rate" :class="{ up: fund.displayRate > 0, down: fund.displayRate < 0 }">
                      {{ fund.displayRate > 0 ? '+' : '' }}{{ fund.displayRate.toFixed(2) }}%
                    </span>
                  </div>
                  <el-empty v-if="topChanges.topLosers.length === 0" description="暂无数据" :image-size="40" />
                </div>
              </div>
            </div>
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
            <span>分析时间：{{ formatDateTime(portfolioAnalysis.timestamp) }}</span>
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

    <!-- 指数选择对话框 -->
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
  </div>
</template>

<style scoped>
.home-page {
  width: 100%;
  max-width: 1400px;
}

/* 卡片入场动画 */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

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

.stat-card {
  animation: fadeInUp 0.5s ease-out backwards;
}

.stat-card:nth-child(1) { animation-delay: 0s; }
.stat-card:nth-child(2) { animation-delay: 0.1s; }
.stat-card:nth-child(3) { animation-delay: 0.2s; }
.stat-card:nth-child(4) { animation-delay: 0.3s; }
.stat-card:nth-child(5) { animation-delay: 0.4s; }

.data-card {
  animation: scaleIn 0.4s ease-out backwards;
}

/* 列表项入场动画 */
@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.holding-item,
.trade-item,
.rank-item {
  animation: slideInLeft 0.3s ease-out backwards;
}

/* 交错动画延迟 */
.holding-item:nth-child(1),
.trade-item:nth-child(1) { animation-delay: 0s; }

.holding-item:nth-child(2),
.trade-item:nth-child(2) { animation-delay: 0.05s; }

.holding-item:nth-child(3),
.trade-item:nth-child(3) { animation-delay: 0.1s; }

.holding-item:nth-child(4),
.trade-item:nth-child(4) { animation-delay: 0.15s; }

.holding-item:nth-child(5),
.trade-item:nth-child(5) { animation-delay: 0.2s; }

.holding-item:nth-child(6),
.trade-item:nth-child(6) { animation-delay: 0.25s; }

/* 数字变化动画 */
@keyframes countUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.stat-value {
  animation: countUp 0.6s ease-out;
}

/* 脉冲动画（用于强调） */
@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.02);
  }
}

.stat-card.highlight {
  animation: pulse 2s ease-in-out infinite;
}

/* 字体层级规范 */
.text-h1 { font-size: 24px; font-weight: 700; line-height: 1.4; }
.text-h2 { font-size: 20px; font-weight: 600; line-height: 1.4; }
.text-h3 { font-size: 16px; font-weight: 600; line-height: 1.4; }
.text-body { font-size: 14px; font-weight: 400; line-height: 1.5; }
.text-caption { font-size: 12px; font-weight: 400; line-height: 1.5; color: #909399; }
.text-small { font-size: 11px; font-weight: 400; line-height: 1.4; color: #a8abb2; }

/* 统计卡片 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (max-width: 1400px) {
  .stats-row {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 992px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
}

@media (max-width: 576px) {
  .stats-row {
    grid-template-columns: 1fr;
    gap: 10px;
  }
}

.stat-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 6px 20px rgba(0, 0, 0, 0.04);
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.10);
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
  background: #fff;
  border: 2px solid #e0f2fe;
}

.stat-card.highlight .stat-label,
.stat-card.highlight .stat-hint {
  color: #64748b;
}

.stat-card.highlight .stat-value {
  color: #1e293b;
}

.stat-card.highlight .stat-icon {
  background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);
}

.stat-card.highlight.profit .stat-value,
.stat-card.highlight.profit .stat-sub {
  color: #dc2626;
}

.stat-card.highlight.loss .stat-value,
.stat-card.highlight.loss .stat-sub {
  color: #16a34a;
}

/* 总盈亏卡片涨跌颜色 */
.stat-card.profit .stat-value {
  color: #dc2626;
}

.stat-card.loss .stat-value {
  color: #16a34a;
}

/* 操作按钮 */
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

/* 数据卡片 */
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

.card-header .header-stats {
  display: flex;
  gap: 8px;
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

.card-body {
  padding: 16px 20px;
  flex: 1;
  min-height: 0;
}

/* 统一空状态样式 */
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

/* 骨架屏样式 */
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

/* 全局加载动画 */
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

.chart-container {
  width: 100%;
  height: 240px;
  overflow: hidden;
}

/* 历史收益摘要 */
.history-summary {
  font-size: 14px;
  font-weight: 600;
}

.history-summary.profit {
  color: #dc2626;
}

.history-summary.loss {
  color: #16a34a;
}

/* 市场指数 */
.indices-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 12px;
  height: 240px;
}

/* 确保 el-scrollbar 在卡片内高度一致 */
.card-body .el-scrollbar {
  height: 240px !important;
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

.item-left .meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.item-left .code {
  font-size: 12px;
  color: #909399;
}

.item-left .price-date {
  font-size: 11px;
  color: #c0c4cc;
  background: #f5f7fa;
  padding: 1px 4px;
  border-radius: 3px;
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
  color: #dc2626;
  background: rgba(220, 38, 38, 0.1);
}

.today-change.negative {
  color: #16a34a;
  background: rgba(22, 163, 74, 0.1);
}

.amount.buy {
  color: #dc2626;
  font-weight: 600;
}

.amount.sell {
  color: #16a34a;
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
  background: #f8fafc;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #f1f5f9;
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
  color: #dc2626;
}

.negative {
  color: #16a34a;
}

/* 卡片头部操作按钮 */
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.update-time {
  font-size: 12px;
  color: #909399;
}

/* 涨跌排行 */
.change-rank-container {
  display: flex;
  gap: 20px;
  height: 240px;
}

.rank-section {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.rank-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.rank-title.up {
  color: #dc2626;
}

.rank-title.down {
  color: #16a34a;
}

.rank-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rank-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: #f8fafc;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.rank-item:hover {
  background: #f0f7ff;
  border-color: #1890ff;
}

.rank-num {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e2e8f0;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  flex-shrink: 0;
}

.rank-item:nth-child(1) .rank-num {
  background: #fef3c7;
  color: #d97706;
}

.rank-item:nth-child(2) .rank-num {
  background: #f1f5f9;
  color: #64748b;
}

.rank-item:nth-child(3) .rank-num {
  background: #ffedd5;
  color: #9a3412;
}

.rank-name {
  flex: 1;
  font-size: 12px;
  color: #1a1a2e;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rank-rate {
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.rank-rate.up {
  color: #dc2626;
}

.rank-rate.down {
  color: #16a34a;
}

/* 自定义滚动条样式 */
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

/* Firefox 滚动条 */
* {
  scrollbar-width: thin;
  scrollbar-color: #d1d5db transparent;
}

/* Element Plus 滚动条容器 */
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

/* 指数选择对话框 */
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