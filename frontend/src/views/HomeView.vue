<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/funds'
import { aiAPI, marketAPI } from '@/api'
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
async function loadIndices(skipCache = false) {
  indicesLoading.value = true
  try {
    const result = await marketAPI.getIndices(skipCache)
    indicesData.value = result.data || []
    indicesDate.value = result.date || ''
    indicesIsToday.value = result.is_today !== false
    indicesUpdateTime.value = result.update_time || ''
  } catch (error) {
    console.error('加载市场指数失败:', error)
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
      <el-col :span="12">
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

/* 统计卡片 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 24px;
  margin-bottom: 24px;
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
}

.data-card:hover {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.10);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #f0f0f0;
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
  padding: 20px 24px;
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