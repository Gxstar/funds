<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  chartData: Object,
  period: String,
  syncing: Boolean
})

const emit = defineEmits(['update:period', 'sync'])

const chartRef = ref(null)
let chartInstance = null

function initChart() {
  if (!chartRef.value || !props.chartData) return

  chartInstance?.dispose()
  chartInstance = echarts.init(chartRef.value)

  const data = props.chartData
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

function handleResize() {
  chartInstance?.resize()
}

function changePeriod(p) {
  emit('update:period', p)
}

watch(() => props.chartData, () => {
  nextTick(() => initChart())
})

onMounted(() => {
  if (props.chartData) {
    nextTick(() => initChart())
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
  <div class="info-card">
    <div class="info-header">
      <span class="section-title">净值走势</span>
      <el-space>
        <el-radio-group :model-value="period" size="small" @change="changePeriod">
          <el-radio-button value="3m">3月</el-radio-button>
          <el-radio-button value="6m">6月</el-radio-button>
          <el-radio-button value="1y">1年</el-radio-button>
          <el-radio-button value="3y">3年</el-radio-button>
          <el-radio-button value="5y">5年</el-radio-button>
          <el-radio-button value="all">全部</el-radio-button>
        </el-radio-group>
        <el-tooltip content="同步最新净值" placement="top">
          <el-button size="small" :loading="syncing" @click="emit('sync')">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </el-tooltip>
      </el-space>
    </div>
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<style scoped>
.info-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 6px 20px rgba(0, 0, 0, 0.04);
  transition: all 0.3s;
}

.info-card:hover {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.10);
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
}

.chart-container {
  width: 100%;
  height: 350px;
}
</style>
