<script setup>
import { formatCurrency, formatPercent } from '@/utils/format'

defineProps({
  fund: Object,
  holding: Object
})

const emit = defineEmits(['set-etf', 'delete'])
</script>

<template>
  <div class="fund-header-stats">
    <div class="fund-title-bar">
      <div class="fund-title-left">
        <span class="fund-name">{{ fund?.fund_name || '加载中...' }}</span>
        <el-tag size="small" type="info" class="fund-code-tag">{{ fund?.fund_code }}</el-tag>
        <el-tag v-if="fund?.fund_type" size="small" type="primary" class="fund-type-tag">{{ fund.fund_type }}</el-tag>
      </div>
      <el-space>
        <el-button size="small" @click="emit('set-etf')">设置ETF</el-button>
        <el-button size="small" type="danger" @click="emit('delete')">删除</el-button>
      </el-space>
    </div>

    <div class="stats-row">
      <div class="stat-item">
        <div class="stat-label">当前净值</div>
        <div class="stat-value">{{ fund?.last_net_value?.toFixed(4) || '-' }}</div>
      </div>
      <div class="stat-item" :class="{ profit: fund?.last_growth_rate > 0, loss: fund?.last_growth_rate < 0 }">
        <div class="stat-label">日涨跌幅</div>
        <div class="stat-value">
          {{ fund?.last_growth_rate ? formatPercent(fund.last_growth_rate) : '-' }}
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-label">关联ETF</div>
        <div class="stat-value">
          <el-link v-if="fund?.related_etf" type="primary" @click="emit('set-etf')">{{ fund.related_etf }}</el-link>
          <span v-else class="text-secondary">未设置</span>
        </div>
      </div>
      <div v-if="holding" class="stat-item" :class="{ profit: holding.profit > 0, loss: holding.profit < 0 }">
        <div class="stat-label">持仓盈亏</div>
        <div class="stat-value">{{ formatCurrency(holding.profit) }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fund-header-stats {
  background: #fff;
  border-radius: 16px;
  padding: 20px 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 6px 20px rgba(0, 0, 0, 0.04);
  transition: all 0.3s;
}

.fund-header-stats:hover {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.10);
}

.fund-title-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.fund-title-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fund-name {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
}

.fund-code-tag,
.fund-type-tag {
  font-size: 12px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #f1f5f9;
  transition: all 0.2s;
}

.stat-item:hover {
  background: #f1f5f9;
  transform: translateY(-2px);
}

.stat-item .stat-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}

.stat-item .stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.stat-item.profit {
  background: rgba(220, 38, 38, 0.05);
  border-color: rgba(220, 38, 38, 0.1);
}

.stat-item.profit .stat-value {
  color: #dc2626;
}

.stat-item.loss {
  background: rgba(22, 163, 74, 0.05);
  border-color: rgba(22, 163, 74, 0.1);
}

.stat-item.loss .stat-value {
  color: #16a34a;
}

.positive { color: #d32f2f; }
.negative { color: #388e3c; }
.text-secondary { color: #909399; }
.text-xs { font-size: 12px; }
</style>
