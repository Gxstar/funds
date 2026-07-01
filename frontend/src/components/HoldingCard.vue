<script setup>
import { formatCurrency, formatPercent } from '@/utils/format'

defineProps({
  fund: Object,
  holding: Object
})

const emit = defineEmits(['buy', 'sell', 'set-holding', 'show-trades'])
</script>

<template>
  <div class="info-card holding-card">
    <div class="info-header">
      <span class="section-title">持仓信息</span>
      <el-button size="small" text type="primary" @click="emit('show-trades')">交易记录</el-button>
    </div>
    <div class="card-content">
      <template v-if="holding">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="持有份额">{{ holding.shares.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="成本价">{{ holding.costPrice.toFixed(4) }}</el-descriptions-item>
          <el-descriptions-item label="当前市值">{{ formatCurrency(holding.marketValue) }}</el-descriptions-item>
          <el-descriptions-item label="盈亏金额">
            <span :class="{ positive: holding.profit > 0, negative: holding.profit < 0 }">
              {{ formatCurrency(holding.profit) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="盈亏比例" :span="2">
            <span :class="{ positive: holding.profitRate > 0, negative: holding.profitRate < 0 }">
              {{ formatPercent(holding.profitRate) }}
            </span>
          </el-descriptions-item>
        </el-descriptions>
      </template>
      <el-empty v-else description="暂无持仓，点击买入开始投资" :image-size="50" />
    </div>
    <el-divider style="margin: 12px 0" />
    <el-space>
      <el-button class="btn-buy" @click="emit('buy')">买入</el-button>
      <el-button v-if="holding" class="btn-sell" @click="emit('sell')">卖出</el-button>
      <el-button @click="emit('set-holding')">设置持仓</el-button>
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

.btn-buy {
  background: #dc2626;
  border-color: #dc2626;
  color: #fff;
}

.btn-buy:hover {
  background: #b91c1c;
  border-color: #b91c1c;
}

.btn-sell {
  background: #16a34a;
  border-color: #16a34a;
  color: #fff;
}

.btn-sell:hover {
  background: #15803d;
  border-color: #15803d;
}

.positive { color: #d32f2f; }
.negative { color: #388e3c; }
</style>
