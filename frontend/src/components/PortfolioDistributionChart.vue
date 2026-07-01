<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  holdings: { type: Array, default: () => [] }
})

const chartType = ref('pie')
const pieChart = ref(null)
let chartInstance = null

function updateChart() {
  if (!chartInstance) return

  const holdings = props.holdings
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

const handleResize = () => {
  chartInstance?.resize()
}

watch(() => props.holdings, () => updateChart(), { deep: true })

onMounted(() => {
  chartInstance = echarts.init(pieChart.value)
  updateChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
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
</style>
