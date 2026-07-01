<script setup>
import { formatCurrency } from '@/utils/format'

defineProps({
  trades: { type: Array, default: () => [] }
})

const emit = defineEmits(['click-fund'])
</script>

<template>
  <el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
    <div class="data-card">
      <div class="card-header">
        <span class="title">近期交易</span>
      </div>
      <div class="card-body">
        <el-scrollbar height="240px">
          <div class="list-container">
            <div
              v-for="trade in trades"
              :key="trade.id"
              class="trade-item"
              @click="$emit('click-fund', trade.fund_code)"
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
            <el-empty v-if="trades.length === 0" description="暂无交易记录" :image-size="60" />
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

.trade-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.2s;
  animation: slideInLeft 0.3s ease-out backwards;
}

.trade-item:last-child {
  border-bottom: none;
}

.trade-item:hover {
  background: #fafafa;
  margin: 0 -20px;
  padding: 12px 20px;
}

.trade-item:nth-child(1) { animation-delay: 0s; }
.trade-item:nth-child(2) { animation-delay: 0.05s; }
.trade-item:nth-child(3) { animation-delay: 0.1s; }
.trade-item:nth-child(4) { animation-delay: 0.15s; }
.trade-item:nth-child(5) { animation-delay: 0.2s; }
.trade-item:nth-child(6) { animation-delay: 0.25s; }

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

.item-left .code {
  font-size: 12px;
  color: #909399;
}

.item-right {
  text-align: right;
}

.amount.buy {
  color: #dc2626;
  font-weight: 600;
}

.amount.sell {
  color: #16a34a;
  font-weight: 600;
}
</style>
