<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useFundStore } from '@/stores/funds'
import { etfAPI, tradeAPI } from '@/api'
import * as echarts from 'echarts'
import { marked } from 'marked'

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true
})

const route = useRoute()
const router = useRouter()
const fundStore = useFundStore()

const loading = ref(true)
const period = ref('1y')
const chartRef = ref(null)
let chartInstance = null

// 弹窗状态
const tradeDialogVisible = ref(false)
const tradeType = ref('BUY')
const holdingDialogVisible = ref(false)
const etfDialogVisible = ref(false)
const tradeHistoryVisible = ref(false)
const allTrades = ref([])
const editingTrade = ref(null)
const editTradeDialogVisible = ref(false)
const editTradeForm = ref({
  id: null,
  trade_type: 'BUY',
  trade_date: '',
  confirm_date: '',
  amount: '',
  confirm_net_value: '',
  confirm_shares: ''
})

// 交易表单
const tradeForm = ref({
  trade_date: '',
  confirm_date: '',
  amount: '',
  confirm_net_value: '',
  confirm_shares: ''
})

// 持仓表单
const holdingForm = ref({
  total_shares: '',
  cost_price: '',
  total_cost: ''
})

// ETF 表单
const etfForm = ref({
  etf_code: ''
})

// 推荐 ETF 列表
const recommendedEtfs = ref([])

// 当前基金
const fund = computed(() => fundStore.currentFund)

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

// 持仓信息计算
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

// 加载基金数据
async function loadFundData() {
  const code = route.params.code
  if (!code) return
  
  loading.value = true
  try {
    await fundStore.selectFund(code)
    setTimeout(initChart, 100)
    // 自动加载AI缓存
    await fundStore.loadAICache(code)
  } catch (error) {
    ElMessage.error('加载基金详情失败')
    router.push('/')
  } finally {
    loading.value = false
  }
}

// 初始化图表
function initChart() {
  if (!chartRef.value || !fundStore.chartData) return
  
  chartInstance?.dispose()
  chartInstance = echarts.init(chartRef.value)
  
  const data = fundStore.chartData
  if (!data.dates || data.dates.length === 0) {
    chartInstance.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#909399' } }
    })
    return
  }
  
  const indicators = data.indicators || {}
  const trades = data.trades || { buy: [], sell: [] }
  
  chartInstance.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: {
      data: ['净值', 'MA5', 'MA10', 'MA20', '买入', '卖出'],
      bottom: 0,
      selected: { '净值': true, 'MA5': false, 'MA10': false, 'MA20': false, '买入': true, '卖出': true }
    },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: data.dates, boundaryGap: false },
    yAxis: { type: 'value', scale: true },
    series: [
      {
        name: '净值', type: 'line', data: data.values, showSymbol: false,
        lineStyle: { width: 2 }, itemStyle: { color: '#409eff' }
      },
      { name: 'MA5', type: 'line', data: indicators.ma5, showSymbol: false, lineStyle: { width: 1 }, itemStyle: { color: '#e6a23c' } },
      { name: 'MA10', type: 'line', data: indicators.ma10, showSymbol: false, lineStyle: { width: 1 }, itemStyle: { color: '#67c23a' } },
      { name: 'MA20', type: 'line', data: indicators.ma20, showSymbol: false, lineStyle: { width: 1 }, itemStyle: { color: '#909399' } },
      { name: '买入', type: 'scatter', data: trades.buy, symbol: 'circle', symbolSize: 10, itemStyle: { color: '#f56c6c', borderColor: '#fff', borderWidth: 2 }, z: 10 },
      { name: '卖出', type: 'scatter', data: trades.sell, symbol: 'circle', symbolSize: 10, itemStyle: { color: '#67c23a', borderColor: '#fff', borderWidth: 2 }, z: 10 }
    ]
  })
}

// 切换时间周期
async function changePeriod(p) {
  period.value = p
  await fundStore.loadChartData(route.params.code, p)
  initChart()
}

// 显示交易弹窗
function showTradeDialog(type) {
  tradeType.value = type
  const today = new Date().toISOString().split('T')[0]
  tradeForm.value = { trade_date: today, confirm_date: today, amount: '', confirm_net_value: '', confirm_shares: '' }
  tradeDialogVisible.value = true
}

// 计算份额
function calculateShares() {
  const amount = parseFloat(tradeForm.value.amount)
  const netValue = parseFloat(tradeForm.value.confirm_net_value)
  if (amount && netValue) {
    tradeForm.value.confirm_shares = (amount / netValue).toFixed(2)
  }
}

// 提交交易
async function submitTrade() {
  try {
    await fundStore.addTrade({
      fund_code: route.params.code,
      trade_type: tradeType.value,
      ...tradeForm.value
    })
    tradeDialogVisible.value = false
    ElMessage.success('交易记录已保存')
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  }
}

// 显示持仓设置
function showHoldingDialog() {
  holdingForm.value = {
    total_shares: fund.value?.total_shares || '',
    cost_price: fund.value?.cost_price || '',
    total_cost: fund.value?.total_cost || ''
  }
  holdingDialogVisible.value = true
}

// 计算总投入
function calculateTotalCost() {
  const shares = parseFloat(holdingForm.value.total_shares)
  const costPrice = parseFloat(holdingForm.value.cost_price)
  if (shares && costPrice) {
    holdingForm.value.total_cost = (shares * costPrice).toFixed(2)
  }
}

// 保存持仓
async function saveHolding() {
  try {
    await fundStore.updateHolding(route.params.code, holdingForm.value)
    holdingDialogVisible.value = false
    ElMessage.success('持仓已保存')
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  }
}

// 清空持仓
async function clearHolding() {
  try {
    await ElMessageBox.confirm('确定要清空该基金的持仓吗？', '警告', { type: 'warning' })
    await fundStore.updateHolding(route.params.code, { total_shares: '0', cost_price: '0', total_cost: '0' })
    holdingDialogVisible.value = false
    ElMessage.success('持仓已清空')
  } catch (e) {}
}

// 保存 ETF
async function saveETF() {
  try {
    await fundStore.setRelatedETF(route.params.code, etfForm.value.etf_code)
    etfDialogVisible.value = false
    ElMessage.success('ETF 关联已保存')
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  }
}

// 清除 ETF
async function clearETF() {
  try {
    await fundStore.setRelatedETF(route.params.code, null)
    etfDialogVisible.value = false
    ElMessage.success('ETF 关联已清除')
  } catch (error) {
    ElMessage.error(error.message || '清除失败')
  }
}

// 显示交易历史
async function showTradeHistory() {
  try {
    const result = await tradeAPI.getAll(route.params.code, 100)
    allTrades.value = result.data || []
  } catch (error) {
    allTrades.value = []
  }
  tradeHistoryVisible.value = true
}

// 删除基金
async function deleteFund() {
  try {
    await ElMessageBox.confirm('确定要删除该基金吗？这将同时删除相关的持仓和交易记录。', '警告', { type: 'warning' })
    emit('delete-fund', route.params.code)
  } catch (e) {}
}

// AI 分析
async function getAIAnalysis(forceRefresh = false) {
  try {
    await fundStore.getAISuggestion(route.params.code, forceRefresh)
  } catch (error) {
    ElMessage.error(error.message || '分析失败')
  }
}

// 编辑交易
function editTrade(trade) {
  editingTrade.value = trade
  editTradeForm.value = {
    id: trade.id,
    trade_type: trade.trade_type,
    trade_date: trade.trade_date,
    confirm_date: trade.confirm_date || '',
    amount: String(trade.amount),
    confirm_net_value: trade.confirm_net_value ? String(trade.confirm_net_value) : '',
    confirm_shares: trade.confirm_shares ? String(trade.confirm_shares) : ''
  }
  editTradeDialogVisible.value = true
}

// 保存编辑的交易
async function saveEditTrade() {
  try {
    await fundStore.updateTrade(editTradeForm.value.id, {
      trade_type: editTradeForm.value.trade_type,
      trade_date: editTradeForm.value.trade_date,
      confirm_date: editTradeForm.value.confirm_date || null,
      amount: editTradeForm.value.amount,
      confirm_net_value: editTradeForm.value.confirm_net_value || null,
      confirm_shares: editTradeForm.value.confirm_shares || null,
      fund_code: route.params.code
    })
    editTradeDialogVisible.value = false
    // 刷新交易历史
    const result = await tradeAPI.getAll(route.params.code, 100)
    allTrades.value = result.data || []
    ElMessage.success('交易记录已更新')
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  }
}

// 删除交易
async function deleteTrade(tradeId) {
  try {
    await ElMessageBox.confirm('确定删除该交易记录？', '警告', { type: 'warning' })
    await fundStore.deleteTrade(tradeId, route.params.code)
    // 刷新交易历史
    const result = await tradeAPI.getAll(route.params.code, 100)
    allTrades.value = result.data || []
    ElMessage.success('交易记录已删除')
  } catch (e) {}
}

// 显示 ETF 设置
async function showETFDialog() {
  etfForm.value.etf_code = fund.value?.related_etf || ''
  // 加载推荐 ETF
  if (fund.value?.fund_type) {
    try {
      const result = await etfAPI.getRecommended(fund.value.fund_type)
      recommendedEtfs.value = result.data || []
    } catch (error) {
      recommendedEtfs.value = []
    }
  }
  etfDialogVisible.value = true
}

// 选择推荐 ETF
function selectRecommendedEtf(code) {
  etfForm.value.etf_code = code
}

// 渲染 Markdown
function renderMarkdown(text) {
  if (!text) return ''
  return marked(text)
}

const emit = defineEmits(['delete-fund'])

// 切换基金时清空AI分析结果
watch(() => route.params.code, (newCode, oldCode) => {
  if (oldCode && newCode !== oldCode) {
    fundStore.clearAIAnalysis()
  }
})

// 加载基金数据
watch(() => route.params.code, (code) => {
  if (code) {
    loadFundData()
  }
}, { immediate: true })

onMounted(() => {
  window.addEventListener('resize', () => chartInstance?.resize())
})

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', () => chartInstance?.resize())
})
</script>

<template>
  <div v-loading="loading" class="fund-detail">
    <!-- 基金基本信息 -->
    <div class="info-card">
      <div class="info-header">
        <div class="fund-title">
          <span class="fund-name">{{ fund?.fund_name || '加载中...' }}</span>
          <el-tag>{{ fund?.fund_code }}</el-tag>
        </div>
        <el-space>
          <el-button size="small" @click="showETFDialog">设置ETF</el-button>
          <el-button size="small" type="danger" @click="deleteFund">删除</el-button>
        </el-space>
      </div>
      <el-descriptions :column="5" border size="small">
        <el-descriptions-item label="基金类型">{{ fund?.fund_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="风险等级">{{ fund?.risk_level || '-' }}</el-descriptions-item>
        <el-descriptions-item label="当前净值">{{ fund?.last_net_value?.toFixed(4) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="日涨跌幅">
          <span :class="{ positive: fund?.last_growth_rate > 0, negative: fund?.last_growth_rate < 0 }">
            {{ fund?.last_growth_rate ? formatPercent(fund.last_growth_rate) : '-' }}
          </span>
          <span v-if="fund?.last_price_date" class="text-secondary">({{ fund.last_price_date }})</span>
        </el-descriptions-item>
        <el-descriptions-item label="关联ETF">
          <el-link v-if="fund?.related_etf" type="primary" @click="showETFDialog">{{ fund.related_etf }}</el-link>
          <span v-else class="text-secondary">未设置</span>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- 持仓信息和 ETF 行情 -->
    <el-row :gutter="16">
      <el-col :span="fund?.related_etf ? 12 : 24">
        <div class="info-card holding-card">
          <div class="info-header">
            <span class="section-title">持仓信息</span>
            <el-button size="small" text type="primary" @click="showTradeHistory">交易记录</el-button>
          </div>
          <div class="card-content">
            <template v-if="holdingInfo">
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="持有份额">{{ holdingInfo.shares.toFixed(2) }}</el-descriptions-item>
                <el-descriptions-item label="成本价">{{ holdingInfo.costPrice.toFixed(4) }}</el-descriptions-item>
                <el-descriptions-item label="当前市值">{{ formatCurrency(holdingInfo.marketValue) }}</el-descriptions-item>
                <el-descriptions-item label="盈亏金额">
                  <span :class="{ positive: holdingInfo.profit > 0, negative: holdingInfo.profit < 0 }">
                    {{ formatCurrency(holdingInfo.profit) }}
                  </span>
                </el-descriptions-item>
                <el-descriptions-item label="盈亏比例" :span="2">
                  <span :class="{ positive: holdingInfo.profitRate > 0, negative: holdingInfo.profitRate < 0 }">
                    {{ formatPercent(holdingInfo.profitRate) }}
                  </span>
                </el-descriptions-item>
              </el-descriptions>
            </template>
            <el-empty v-else description="暂无持仓，点击买入开始投资" :image-size="50" />
          </div>
          <el-divider style="margin: 12px 0" />
          <el-space>
            <el-button type="primary" @click="showTradeDialog('BUY')">买入</el-button>
            <el-button v-if="holdingInfo" type="danger" @click="showTradeDialog('SELL')">卖出</el-button>
            <el-button @click="showHoldingDialog">设置持仓</el-button>
          </el-space>
        </div>
      </el-col>
      
      <el-col v-if="fund?.related_etf" :span="12">
        <div class="info-card holding-card">
          <div class="info-header">
            <span class="section-title">ETF 实时行情</span>
            <span class="text-secondary text-xs">{{ fundStore.etfData?.realtime?.cached_at || '' }}</span>
          </div>
          <div class="card-content">
            <template v-if="fundStore.etfData?.available">
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="ETF代码">{{ fundStore.etfData?.realtime?.code || fund.related_etf }}</el-descriptions-item>
                <el-descriptions-item label="ETF名称">{{ fundStore.etfData?.realtime?.name || '-' }}</el-descriptions-item>
                <el-descriptions-item label="当前价格">{{ fundStore.etfData?.realtime?.current_price || '-' }}</el-descriptions-item>
                <el-descriptions-item label="当日涨跌">
                  <span :class="{ positive: fundStore.etfData?.realtime?.change_pct > 0, negative: fundStore.etfData?.realtime?.change_pct < 0 }">
                    {{ fundStore.etfData?.realtime?.change_pct ? formatPercent(fundStore.etfData.realtime.change_pct) : '-' }}
                  </span>
                </el-descriptions-item>
                <el-descriptions-item label="今开/昨收">{{ fundStore.etfData?.realtime?.open || '-' }} / {{ fundStore.etfData?.realtime?.pre_close || '-' }}</el-descriptions-item>
                <el-descriptions-item label="最高/最低">{{ fundStore.etfData?.realtime?.high || '-' }} / {{ fundStore.etfData?.realtime?.low || '-' }}</el-descriptions-item>
              </el-descriptions>
            </template>
            <el-empty v-else description="ETF 数据暂不可用" :image-size="50" />
          </div>
          <el-divider style="margin: 12px 0" />
          <el-space>
            <el-button size="small" @click="showETFDialog">更换ETF</el-button>
          </el-space>
        </div>
      </el-col>
    </el-row>

    <!-- 净值走势 -->
    <div class="info-card">
      <div class="info-header">
        <span class="section-title">净值走势</span>
        <el-radio-group v-model="period" size="small" @change="changePeriod">
          <el-radio-button value="3m">3月</el-radio-button>
          <el-radio-button value="6m">6月</el-radio-button>
          <el-radio-button value="1y">1年</el-radio-button>
          <el-radio-button value="3y">3年</el-radio-button>
          <el-radio-button value="5y">5年</el-radio-button>
          <el-radio-button value="all">全部</el-radio-button>
        </el-radio-group>
      </div>
      <div ref="chartRef" class="chart-container"></div>
    </div>

    <!-- AI 建议 -->
    <div class="info-card">
      <div class="info-header">
        <span class="section-title">AI 建议</span>
        <el-space>
          <el-tag v-if="fundStore.aiAnalysis?.cached" type="success" size="small">缓存</el-tag>
          <el-button 
            v-if="fundStore.aiAnalysis" 
            size="small" 
            :loading="fundStore.aiLoading" 
            @click="getAIAnalysis(true)"
          >
            刷新
          </el-button>
          <el-button 
            v-else 
            type="primary" 
            size="small" 
            :loading="fundStore.aiLoading" 
            @click="getAIAnalysis(false)"
          >
            分析
          </el-button>
        </el-space>
      </div>
      <el-space wrap class="mb-3">
        <el-tag>MA5: {{ fundStore.aiAnalysis?.indicators?.ma5 || '-' }}</el-tag>
        <el-tag>MA10: {{ fundStore.aiAnalysis?.indicators?.ma10 || '-' }}</el-tag>
        <el-tag>MA20: {{ fundStore.aiAnalysis?.indicators?.ma20 || '-' }}</el-tag>
        <el-tag>RSI: {{ fundStore.aiAnalysis?.indicators?.rsi || '-' }}</el-tag>
        <el-tag>MACD: {{ fundStore.aiAnalysis?.indicators?.macd || '-' }}</el-tag>
      </el-space>
      <el-scrollbar v-if="fundStore.aiAnalysis" height="500px" class="ai-result">
        <div v-if="fundStore.aiAnalysis.timestamp" class="ai-time">
          分析时间: {{ new Date(fundStore.aiAnalysis.timestamp).toLocaleString('zh-CN') }}
          <span v-if="fundStore.aiAnalysis.cached" class="cache-hint">（使用缓存，点击刷新获取最新分析）</span>
        </div>
        <div class="markdown-body" v-html="renderMarkdown(fundStore.aiAnalysis.analysis)"></div>
      </el-scrollbar>
      <el-empty v-else description="点击分析按钮获取 AI 建议" :image-size="50" />
    </div>

    <!-- 交易弹窗 -->
    <el-dialog v-model="tradeDialogVisible" :title="tradeType === 'BUY' ? '买入' : '卖出'" width="450px">
      <el-form label-width="100px">
        <el-form-item label="购买时间">
          <el-date-picker v-model="tradeForm.trade_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="确认时间">
          <el-date-picker v-model="tradeForm.confirm_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="金额">
          <el-input v-model="tradeForm.amount" placeholder="成交金额" @input="calculateShares" />
        </el-form-item>
        <el-form-item label="确认净值">
          <el-input v-model="tradeForm.confirm_net_value" placeholder="确认日净值" @input="calculateShares" />
        </el-form-item>
        <el-form-item label="确认份额">
          <el-input v-model="tradeForm.confirm_shares" placeholder="自动计算或手动输入" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tradeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitTrade">确认</el-button>
      </template>
    </el-dialog>

    <!-- 设置持仓弹窗 -->
    <el-dialog v-model="holdingDialogVisible" title="设置持仓" width="450px">
      <p class="hint">直接设置持仓信息，无需逐笔录入交易记录</p>
      <el-form label-width="100px">
        <el-form-item label="持有份额">
          <el-input v-model="holdingForm.total_shares" placeholder="份额" @input="calculateTotalCost" />
        </el-form-item>
        <el-form-item label="成本价">
          <el-input v-model="holdingForm.cost_price" placeholder="单位净值" @input="calculateTotalCost" />
        </el-form-item>
        <el-form-item label="总投入">
          <el-input v-model="holdingForm.total_cost" placeholder="自动计算或手动输入" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="holdingDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="clearHolding">清空持仓</el-button>
        <el-button type="primary" @click="saveHolding">保存</el-button>
      </template>
    </el-dialog>

    <!-- 设置 ETF 弹窗 -->
    <el-dialog v-model="etfDialogVisible" title="设置关联 ETF" width="500px">
      <p class="hint">关联场内 ETF 可获取当日实时行情，辅助盘中决策</p>
      
      <!-- 推荐 ETF 列表 -->
      <div v-if="recommendedEtfs.length > 0" class="recommended-section">
        <div class="section-label">推荐 ETF</div>
        <div class="recommended-list">
          <el-tag
            v-for="etf in recommendedEtfs"
            :key="etf.code"
            :class="['recommended-tag', { selected: etfForm.etf_code === etf.code }]"
            @click="selectRecommendedEtf(etf.code)"
          >
            {{ etf.code }} {{ etf.name }}
          </el-tag>
        </div>
      </div>
      
      <el-form label-width="100px" style="margin-top: 16px">
        <el-form-item label="ETF代码">
          <el-input v-model="etfForm.etf_code" placeholder="输入6位ETF代码，如 515030" maxlength="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="etfDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="clearETF">清除关联</el-button>
        <el-button type="primary" @click="saveETF">保存</el-button>
      </template>
    </el-dialog>

    <!-- 交易记录弹窗 -->
    <el-dialog v-model="tradeHistoryVisible" title="交易记录" width="900px">
      <el-table :data="allTrades" max-height="400">
        <el-table-column prop="trade_date" label="购买时间" width="110" />
        <el-table-column prop="confirm_date" label="确认时间" width="110" />
        <el-table-column prop="trade_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.trade_type === 'BUY' ? 'danger' : 'success'">
              {{ row.trade_type === 'BUY' ? '买入' : '卖出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confirm_net_value" label="确认净值" width="100">
          <template #default="{ row }">{{ row.confirm_net_value ? parseFloat(row.confirm_net_value).toFixed(4) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="confirm_shares" label="确认份额" width="100">
          <template #default="{ row }">{{ row.confirm_shares ? parseFloat(row.confirm_shares).toFixed(2) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="110">
          <template #default="{ row }">{{ formatCurrency(row.amount) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="editTrade(row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="deleteTrade(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 编辑交易弹窗 -->
    <el-dialog v-model="editTradeDialogVisible" title="编辑交易记录" width="450px">
      <el-form label-width="100px">
        <el-form-item label="交易类型">
          <el-select v-model="editTradeForm.trade_type" style="width: 100%">
            <el-option value="BUY" label="买入" />
            <el-option value="SELL" label="卖出" />
          </el-select>
        </el-form-item>
        <el-form-item label="购买时间">
          <el-date-picker v-model="editTradeForm.trade_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="确认时间">
          <el-date-picker v-model="editTradeForm.confirm_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="金额">
          <el-input v-model="editTradeForm.amount" placeholder="成交金额" />
        </el-form-item>
        <el-form-item label="确认净值">
          <el-input v-model="editTradeForm.confirm_net_value" placeholder="确认日净值" />
        </el-form-item>
        <el-form-item label="确认份额">
          <el-input v-model="editTradeForm.confirm_shares" placeholder="确认份额" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editTradeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEditTrade">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.fund-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.holding-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.holding-card .card-content {
  flex: 1;
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
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

.section-title {
  font-size: 15px;
  font-weight: 600;
}

.chart-container {
  width: 100%;
  height: 350px;
}

.ai-result {
  background: #fafbfc;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e8eaed;
}

.ai-time {
  font-size: 12px;
  color: #909399;
  margin-bottom: 16px;
  padding: 6px 12px;
  background: #fff;
  border-radius: 6px;
  display: inline-block;
  border: 1px solid #e4e7ed;
}

.cache-hint {
  color: #e6a23c;
  margin-left: 8px;
}

.markdown-body {
  line-height: 1.8;
  color: #24292f;
  font-size: 14px;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin-top: 20px;
  margin-bottom: 12px;
  font-weight: 600;
  line-height: 1.4;
  padding: 8px 12px;
  border-radius: 6px;
}

.markdown-body :deep(h1) {
  font-size: 1.1em;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.markdown-body :deep(h2) {
  font-size: 1em;
  background: #e8f4ff;
  color: #1a1a2e;
  border-left: 4px solid #409eff;
}

.markdown-body :deep(h3) {
  font-size: 0.95em;
  background: #f0f9eb;
  color: #1a1a2e;
  border-left: 4px solid #67c23a;
}

.markdown-body :deep(h4) {
  font-size: 0.9em;
  background: #fdf6ec;
  color: #1a1a2e;
  border-left: 4px solid #e6a23c;
}

.markdown-body :deep(p) {
  margin-bottom: 12px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin-bottom: 12px;
  padding-left: 1.5em;
}

.markdown-body :deep(li) {
  margin-bottom: 4px;
}

.markdown-body :deep(strong) {
  font-weight: 600;
  color: #1a1a2e;
  background: #fff3cd;
  padding: 1px 4px;
  border-radius: 3px;
}

.markdown-body :deep(code) {
  background: rgba(175, 184, 193, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace;
}

.markdown-body :deep(pre) {
  background: #282c34;
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
  margin-bottom: 12px;
}

.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
  color: #abb2bf;
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid #409eff;
  padding: 8px 16px;
  margin: 12px 0;
  background: #f0f7ff;
  color: #57606a;
  border-radius: 0 6px 6px 0;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 12px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e8eaed;
  padding: 8px 12px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #667eea;
  color: #fff;
  font-weight: 600;
}

.markdown-body :deep(tr:nth-child(even)) {
  background: #f6f8fa;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 2px solid #e8eaed;
  margin: 20px 0;
}

.markdown-body :deep(a) {
  color: #409eff;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.positive { color: #f56c6c; }
.negative { color: #67c23a; }
.text-secondary { color: #909399; }
.text-xs { font-size: 12px; }
.mb-3 { margin-bottom: 12px; }

/* 弹窗样式 */
.hint {
  color: #909399;
  font-size: 13px;
  margin-bottom: 16px;
}

.recommended-section {
  margin-bottom: 16px;
}

.section-label {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.recommended-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.recommended-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.recommended-tag:hover {
  background: #ecf5ff;
  color: #409eff;
  border-color: #b3d8ff;
}

.recommended-tag.selected {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}
</style>
