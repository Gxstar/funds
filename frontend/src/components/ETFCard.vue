<script setup>
import { formatPercent } from '@/utils/format'

defineProps({
  etfData: Object,
  etfCode: String,
  refreshing: Boolean
})

const emit = defineEmits(['set-etf', 'refresh'])
</script>

<template>
  <div class="info-card holding-card">
    <div class="info-header">
      <span class="section-title">ETF 实时行情</span>
      <el-space>
        <span class="text-secondary text-xs">{{ etfData?.realtime?.cached_at || '' }}</span>
        <el-button size="small" :loading="refreshing" @click="emit('refresh')">刷新</el-button>
      </el-space>
    </div>
    <div class="card-content">
      <template v-if="etfData?.available">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="ETF代码">{{ etfData?.realtime?.code || etfCode }}</el-descriptions-item>
          <el-descriptions-item label="ETF名称">{{ etfData?.realtime?.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="当前价格">{{ etfData?.realtime?.current_price || '-' }}</el-descriptions-item>
          <el-descriptions-item label="当日涨跌">
            <span :class="{ positive: etfData?.realtime?.change_pct > 0, negative: etfData?.realtime?.change_pct < 0 }">
              {{ etfData?.realtime?.change_pct ? formatPercent(etfData.realtime.change_pct) : '-' }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="今开/昨收">{{ etfData?.realtime?.open || '-' }} / {{ etfData?.realtime?.pre_close || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最高/最低">{{ etfData?.realtime?.high || '-' }} / {{ etfData?.realtime?.low || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <el-empty v-else description="ETF 数据暂不可用" :image-size="50" />
    </div>
    <el-divider style="margin: 12px 0" />
    <el-space>
      <el-button size="small" @click="emit('set-etf')">更换ETF</el-button>
    </el-space>
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
  margin-bottom: 20px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
}

.positive { color: #d32f2f; }
.negative { color: #388e3c; }
.text-secondary { color: #909399; }
.text-xs { font-size: 12px; }
</style>
