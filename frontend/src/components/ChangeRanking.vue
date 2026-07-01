<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  holdings: { type: Array, default: () => [] }
})

const emit = defineEmits(['click-fund'])

const changeRankType = ref('daily')

const topChanges = computed(() => {
  const holdings = props.holdings

  if (changeRankType.value === 'daily') {
    const funds = holdings
      .filter(f => f.last_growth_rate !== null && f.last_growth_rate !== undefined)
      .sort((a, b) => parseFloat(b.last_growth_rate) - parseFloat(a.last_growth_rate))

    return {
      topGainers: funds.slice(0, 3).map(f => ({
        ...f,
        displayRate: f.last_growth_rate,
        isDaily: true
      })),
      topLosers: funds.slice(-3).reverse().map(f => ({
        ...f,
        displayRate: f.last_growth_rate,
        isDaily: true
      }))
    }
  } else {
    const funds = holdings
      .filter(f => f.total_cost && parseFloat(f.total_cost) > 0 && f.last_net_value)
      .map(f => {
        const currentValue = parseFloat(f.total_shares || 0) * parseFloat(f.last_net_value || 0)
        const cost = parseFloat(f.total_cost || 0)
        const profitRate = cost > 0 ? ((currentValue - cost) / cost * 100) : 0
        return {
          ...f,
          displayRate: profitRate,
          isDaily: false
        }
      })
      .sort((a, b) => b.displayRate - a.displayRate)

    return {
      topGainers: funds.slice(0, 3),
      topLosers: funds.slice(-3).reverse()
    }
  }
})
</script>

<template>
  <el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
    <div class="data-card">
      <div class="card-header">
        <span class="title">{{ changeRankType === 'daily' ? '涨跌排行' : '收益排行' }}</span>
        <el-button-group size="small">
          <el-button
            :type="changeRankType === 'daily' ? 'primary' : ''"
            @click="changeRankType = 'daily'"
          >
            当日
          </el-button>
          <el-button
            :type="changeRankType === 'hold' ? 'primary' : ''"
            @click="changeRankType = 'hold'"
          >
            持有
          </el-button>
        </el-button-group>
      </div>
      <div class="card-body">
        <div class="change-rank-container">
          <div class="rank-section">
            <div class="rank-title up">
              <el-icon><Top /></el-icon>
              <span>{{ changeRankType === 'daily' ? '涨幅前三' : '收益前三' }}</span>
            </div>
            <div class="rank-list">
              <div
                v-for="(fund, index) in topChanges.topGainers"
                :key="fund.fund_code"
                class="rank-item"
                @click="$emit('click-fund', fund.fund_code)"
              >
                <span class="rank-num">{{ index + 1 }}</span>
                <span class="rank-name">{{ fund.fund_name }}</span>
                <span class="rank-rate" :class="{ up: fund.displayRate > 0, down: fund.displayRate < 0 }">
                  {{ fund.displayRate > 0 ? '+' : '' }}{{ fund.displayRate.toFixed(2) }}%
                </span>
              </div>
              <el-empty v-if="topChanges.topGainers.length === 0" description="暂无数据" :image-size="40" />
            </div>
          </div>
          <div class="rank-section">
            <div class="rank-title down">
              <el-icon><Bottom /></el-icon>
              <span>{{ changeRankType === 'daily' ? '跌幅前三' : '亏损前三' }}</span>
            </div>
            <div class="rank-list">
              <div
                v-for="(fund, index) in topChanges.topLosers"
                :key="fund.fund_code"
                class="rank-item"
                @click="$emit('click-fund', fund.fund_code)"
              >
                <span class="rank-num">{{ index + 1 }}</span>
                <span class="rank-name">{{ fund.fund_name }}</span>
                <span class="rank-rate" :class="{ up: fund.displayRate > 0, down: fund.displayRate < 0 }">
                  {{ fund.displayRate > 0 ? '+' : '' }}{{ fund.displayRate.toFixed(2) }}%
                </span>
              </div>
              <el-empty v-if="topChanges.topLosers.length === 0" description="暂无数据" :image-size="40" />
            </div>
          </div>
        </div>
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

.change-rank-container {
  display: flex;
  gap: 20px;
  height: 240px;
}

.rank-section {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.rank-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.rank-title.up {
  color: #dc2626;
}

.rank-title.down {
  color: #16a34a;
}

.rank-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rank-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: #f8fafc;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  animation: slideInLeft 0.3s ease-out backwards;
}

.rank-item:hover {
  background: #f0f7ff;
  border-color: #1890ff;
}

.rank-num {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e2e8f0;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  flex-shrink: 0;
}

.rank-item:nth-child(1) .rank-num {
  background: #fef3c7;
  color: #d97706;
}

.rank-item:nth-child(2) .rank-num {
  background: #f1f5f9;
  color: #64748b;
}

.rank-item:nth-child(3) .rank-num {
  background: #ffedd5;
  color: #9a3412;
}

.rank-name {
  flex: 1;
  font-size: 12px;
  color: #1a1a2e;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rank-rate {
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.rank-rate.up {
  color: #dc2626;
}

.rank-rate.down {
  color: #16a34a;
}
</style>
