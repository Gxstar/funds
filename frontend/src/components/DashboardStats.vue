<script setup>
import { formatCurrency, formatPercent } from '@/utils/format'

defineProps({
  totalCost: { type: Number, default: 0 },
  totalMarketValue: { type: Number, default: 0 },
  todayProfit: { type: Number, default: 0 },
  totalProfit: { type: Number, default: 0 },
  profitRate: { type: Number, default: 0 },
  positionInfo: { type: Object, default: null }
})
</script>

<template>
  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-icon" style="background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);">
        <el-icon><Wallet /></el-icon>
      </div>
      <div class="stat-content">
        <div class="stat-label">总投入</div>
        <div class="stat-value">{{ formatCurrency(totalCost) }}</div>
      </div>
    </div>

    <div class="stat-card">
      <div class="stat-icon" style="background: linear-gradient(135deg, #10b981 0%, #34d399 100%);">
        <el-icon><TrendCharts /></el-icon>
      </div>
      <div class="stat-content">
        <div class="stat-label">总市值</div>
        <div class="stat-value">{{ formatCurrency(totalMarketValue) }}</div>
      </div>
    </div>

    <div class="stat-card highlight" :class="{ profit: todayProfit > 0, loss: todayProfit < 0 }">
      <div class="stat-icon">
        <el-icon><Sunrise /></el-icon>
      </div>
      <div class="stat-content">
        <div class="stat-label">当日收益</div>
        <div class="stat-value">
          {{ (todayProfit > 0 ? '+' : '') + formatCurrency(todayProfit).slice(1) }}
        </div>
      </div>
    </div>

    <div class="stat-card" :class="{ profit: totalProfit > 0, loss: totalProfit < 0 }">
      <div class="stat-icon" style="background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);">
        <el-icon><DataLine /></el-icon>
      </div>
      <div class="stat-content">
        <div class="stat-label">总盈亏</div>
        <div class="stat-value">
          {{ formatCurrency(totalProfit) }}
          <span class="stat-sub">{{ formatPercent(profitRate) }}</span>
        </div>
      </div>
    </div>

    <div class="stat-card">
      <div class="stat-icon" style="background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);">
        <el-icon><PieChart /></el-icon>
      </div>
      <div class="stat-content">
        <div class="stat-label">当前仓位</div>
        <div class="stat-value" v-if="positionInfo">{{ positionInfo.ratio }}%</div>
        <div class="stat-value" v-else>-</div>
        <div class="stat-hint" v-if="positionInfo">剩余 {{ formatCurrency(positionInfo.available) }}</div>
        <div class="stat-hint" v-else>未设置满仓金额</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes countUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.02);
  }
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (max-width: 1400px) {
  .stats-row {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 992px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
}

@media (max-width: 576px) {
  .stats-row {
    grid-template-columns: 1fr;
    gap: 10px;
  }
}

.stat-card {
  animation: fadeInUp 0.5s ease-out backwards;
}

.stat-card:nth-child(1) { animation-delay: 0s; }
.stat-card:nth-child(2) { animation-delay: 0.1s; }
.stat-card:nth-child(3) { animation-delay: 0.2s; }
.stat-card:nth-child(4) { animation-delay: 0.3s; }
.stat-card:nth-child(5) { animation-delay: 0.4s; }

.stat-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 6px 20px rgba(0, 0, 0, 0.04);
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.10);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 22px;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  animation: countUp 0.6s ease-out;
}

.stat-sub {
  font-size: 14px;
  font-weight: 500;
  display: block;
  margin-top: 2px;
}

.stat-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.stat-card.highlight {
  background: #fff;
  border: 2px solid #e0f2fe;
}

.stat-card.highlight .stat-label,
.stat-card.highlight .stat-hint {
  color: #64748b;
}

.stat-card.highlight .stat-value {
  color: #1e293b;
}

.stat-card.highlight .stat-icon {
  background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);
}

.stat-card.highlight.profit .stat-value,
.stat-card.highlight.profit .stat-sub {
  color: #dc2626;
}

.stat-card.highlight.loss .stat-value,
.stat-card.highlight.loss .stat-sub {
  color: #16a34a;
}

.stat-card.profit .stat-value {
  color: #dc2626;
}

.stat-card.loss .stat-value {
  color: #16a34a;
}

.stat-card.highlight {
  animation: pulse 2s ease-in-out infinite;
}
</style>
