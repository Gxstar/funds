<script setup>
import { computed } from 'vue'
import { formatCurrency } from '@/utils/format'

const props = defineProps({
  holdings: { type: Array, default: () => [] }
})

const emit = defineEmits(['click-fund'])

const sortedHoldings = computed(() => {
  return [...props.holdings].sort((a, b) => {
    const valueA = parseFloat(a.total_shares || 0) * parseFloat(a.last_net_value || 0)
    const valueB = parseFloat(b.total_shares || 0) * parseFloat(b.last_net_value || 0)
    return valueB - valueA
  })
})

const changeStats = computed(() => {
  const funds = props.holdings
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
</script>

<template>
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
              @click="$emit('click-fund', fund.fund_code)"
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

.card-body .el-scrollbar {
  height: 240px !important;
}

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

.list-container {
  margin: -4px 0;
}

.holding-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.2s;
  animation: slideInLeft 0.3s ease-out backwards;
}

.holding-item:last-child {
  border-bottom: none;
}

.holding-item:hover {
  background: #fafafa;
  margin: 0 -20px;
  padding: 12px 20px;
}

.holding-item:nth-child(1) { animation-delay: 0s; }
.holding-item:nth-child(2) { animation-delay: 0.05s; }
.holding-item:nth-child(3) { animation-delay: 0.1s; }
.holding-item:nth-child(4) { animation-delay: 0.15s; }
.holding-item:nth-child(5) { animation-delay: 0.2s; }
.holding-item:nth-child(6) { animation-delay: 0.25s; }

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

.positive {
  color: #dc2626;
}

.negative {
  color: #16a34a;
}
</style>
