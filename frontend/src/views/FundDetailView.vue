<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useFundStore } from '@/stores/funds'
import * as echarts from 'echarts'

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
        name: '净值', type: 'line', data: data.values, smooth: true, showSymbol: false,
        lineStyle: { width: 2 }, itemStyle: { color: '#409eff' },
        areaStyle: {
          color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: 'rgba(64,158,255,0.3)' }, { offset: 1, color: 'rgba(64,158,255,0.05)' }]
          }
        }
      },
      { name: 'MA5', type: 'line', data: indicators.ma5, smooth: true, showSymbol: false, lineStyle: { width: 1, type: 'dashed' }, itemStyle: { color: '#e6a23c' } },
      { name: 'MA10', type: 'line', data: indicators.ma10, smooth: true, showSymbol: false, lineStyle: { width: 1, type: 'dashed' }, itemStyle: { color: '#67c23a' } },
      { name: 'MA20', type: 'line', data: indicators.ma20, smooth: true, showSymbol: false, lineStyle: { width: 1, type: 'dashed' }, itemStyle: { color: '#909399' } },
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

// 显示 ETF 设置
function showETFDialog() {
  etfForm.value.etf_code = fund.value?.related_etf || ''
  etfDialogVisible.value = true
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
    const result = await fundStore.loadTradePreview(route.params.code)
    allTrades.value = result || []
  } catch (error) {}
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
async function getAIAnalysis() {
  try {
    await fundStore.getAISuggestion(route.params.code)
  } catch (error) {
    ElMessage.error(error.message || '分析失败')
  }
}

const emit = defineEmits(['delete-fund'])

watch(() => route.params.code, loadFundData, { immediate: true })

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
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="fund-name">{{ fund?.fund_name || '加载中...' }}</span>
          <div class="header-actions">
            <el-tag>{{ fund?.fund_code }}</el-tag>
            <el-button size="small" @click="showETFDialog">设置ETF</el-button>
            <el-button size="small" type="danger" @click="deleteFund">删除</el-button>
          </div>
        </div>
      </template>
      
      <el-descriptions :column="5" border>
        <el-descriptions-item label="基金类型">{{ fund?.fund_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="风险等级">{{ fund?.risk_level || '-' }}</el-descriptions-item>
        <el-descriptions-item label="当前净值">{{ fund?.last_net_value?.toFixed(4) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="日涨跌幅">
          <span :class="{ positive: fund?.last_growth_rate > 0, negative: fund?.last_growth_rate < 0 }">
            {{ fund?.last_growth_rate ? formatPercent(fund.last_growth_rate) : '-' }}
            <span v-if="fund?.last_price_date" class="date">({{ fund.last_price_date }})</span>
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="关联ETF">
          <el-link v-if="fund?.related_etf" type="primary" @click="showETFDialog">{{ fund.related_etf }}</el-link>
          <span v-else class="muted">未设置</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 持仓信息和 ETF 行情 -->
    <el-row :gutter="20">
      <el-col :span="fund?.related_etf ? 12 : 24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>持仓信息</span>
              <el-button size="small" @click="showTradeHistory">交易记录</el-button>
            </div>
          </template>
          
          <template v-if="holdingInfo">
            <el-descriptions :column="2" border>
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
          <el-empty v-else description="暂无持仓，点击买入开始投资" :image-size="60" />
          
          <div class="action-buttons">
            <el-button type="primary" @click="showTradeDialog('BUY')">买入</el-button>
            <el-button v-if="holdingInfo" type="danger" @click="showTradeDialog('SELL')">卖出</el-button>
            <el-button @click="showHoldingDialog">设置持仓</el-button>
          </div>
        </el-card>
      </el-col>
      
      <el-col v-if="fund?.related_etf" :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>ETF 实时行情</span>
              <span class="update-time">{{ fundStore.etfData?.realtime?.cached_at || '' }}</span>
            </div>
          </template>
          
          <template v-if="fundStore.etfData?.available">
            <el-descriptions :column="2" border>
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
          <el-empty v-else description="ETF 数据暂不可用" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 净值走势 -->
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>净值走势</span>
          <el-radio-group v-model="period" size="small" @change="changePeriod">
            <el-radio-button value="3m">3月</el-radio-button>
            <el-radio-button value="6m">6月</el-radio-button>
            <el-radio-button value="1y">1年</el-radio-button>
            <el-radio-button value="3y">3年</el-radio-button>
            <el-radio-button value="5y">5年</el-radio-button>
            <el-radio-button value="all">全部</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <div ref="chartRef" class="chart-container"></div>
    </el-card>

    <!-- AI 建议 -->
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>AI 建议</span>
          <el-button type="primary" size="small" :loading="fundStore.aiLoading" @click="getAIAnalysis">分析</el-button>
        </div>
      </template>
      
      <!-- 技术指标 -->
      <div class="indicators">
        <el-tag>MA5: {{ fundStore.aiAnalysis?.indicators?.ma5 || '-' }}</el-tag>
        <el-tag>MA10: {{ fundStore.aiAnalysis?.indicators?.ma10 || '-' }}</el-tag>
        <el-tag>MA20: {{ fundStore.aiAnalysis?.indicators?.ma20 || '-' }}</el-tag>
        <el-tag>RSI: {{ fundStore.aiAnalysis?.indicators?.rsi || '-' }}</el-tag>
        <el-tag>MACD: {{ fundStore.aiAnalysis?.indicators?.macd || '-' }}</el-tag>
      </div>
      
      <el-scrollbar v-if="fundStore.aiAnalysis" height="300px" class="ai-result">
        <div class="markdown-body" v-html="fundStore.aiAnalysis.analysis"></div>
      </el-scrollbar>
      <el-empty v-else description="点击分析按钮获取 AI 建议" :image-size="60" />
    </el-card>

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
    <el-dialog v-model="etfDialogVisible" title="设置关联 ETF" width="450px">
      <p class="hint">关联场内 ETF 可获取当日实时行情，辅助盘中决策</p>
      <el-form label-width="100px">
        <el-form-item label="ETF代码">
          <el-input v-model="etfForm.etf_code" placeholder="输入6位ETF代码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="etfDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="clearETF">清除关联</el-button>
        <el-button type="primary" @click="saveETF">保存</el-button>
      </template>
    </el-dialog>

    <!-- 交易记录弹窗 -->
    <el-dialog v-model="tradeHistoryVisible" title="交易记录" width="800px">
      <el-table :data="allTrades" max-height="400">
        <el-table-column prop="trade_date" label="购买时间" width="120" />
        <el-table-column prop="confirm_date" label="确认时间" width="120" />
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
        <el-table-column prop="confirm_shares" label="确认份额" width="120">
          <template #default="{ row }">{{ row.confirm_shares ? parseFloat(row.confirm_shares).toFixed(2) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="{ row }">{{ formatCurrency(row.amount) }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<style scoped>
.fund-detail {
  max-width: 1400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.fund-name {
  font-size: 18px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.action-buttons {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.chart-container {
  width: 100%;
  height: 350px;
}

.indicators {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.ai-result {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
}

.hint {
  color: #909399;
  font-size: 13px;
  margin-bottom: 16px;
}

.muted {
  color: #909399;
}

.date {
  font-size: 12px;
  color: #909399;
  margin-left: 4px;
}

.positive {
  color: #f56c6c;
}

.negative {
  color: #67c23a;
}

.update-time {
  font-size: 12px;
  color: #909399;
}

.markdown-body {
  line-height: 1.8;
}
</style>
