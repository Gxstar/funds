<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { formatCurrency } from '@/utils/format'

const props = defineProps({
  history: {
    type: Object,
    default: () => ({ dates: [], market_values: [], costs: [], profits: [], profit_rates: [] })
  },
  loading: { type: Boolean, default: false }
})

const portfolioHistoryChart = ref(null)
let historyChartInstance = null

function initChart() {
  if (!portfolioHistoryChart.value) return

  if (historyChartInstance) {
    historyChartInstance.dispose()
  }

  historyChartInstance = echarts.init(portfolioHistoryChart.value)

  const { dates, profits, profit_rates } = props.history

  if (dates.length === 0) {
    historyChartInstance.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#909399' } }
    }, true)
    return
  }

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

const handleResize = () => {
  historyChartInstance?.resize()
}

watch(() => props.history, () => initChart(), { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  historyChartInstance?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
  <el-col :span="12">
    <div class="data-card">
      <div class="card-header">
        <span class="title">历史收益</span>
        <div class="header-stats" v-if="history.profits.length > 0">
          <span class="history-summary" :class="{ profit: history.profits[history.profits.length - 1] >= 0, loss: history.profits[history.profits.length - 1] < 0 }">
            {{ history.profits[history.profits.length - 1] >= 0 ? '+' : '' }}{{ formatCurrency(history.profits[history.profits.length - 1]) }}
          </span>
        </div>
      </div>
      <div class="card-body">
        <div ref="portfolioHistoryChart" class="chart-container" v-loading="loading"></div>
      </div>
    </div>
  </el-col>
</template>

<style scoped>
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

.data-card {
  animation: scaleIn 0.4s ease-out backwards;
}

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

.card-body {
  padding: 16px 20px;
  flex: 1;
  min-height: 0;
}

.chart-container {
  width: 100%;
  height: 240px;
  overflow: hidden;
}

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
</style>
