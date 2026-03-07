<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, MagicStick } from '@element-plus/icons-vue'
import { useFundStore } from '@/stores/funds'
import { formatCurrency, formatPercent } from '@/utils/format'

const router = useRouter()
const fundStore = useFundStore()

// Props
const props = defineProps({
  aiLoading: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['ai-analysis'])

const searchKeyword = ref('')
const searchResults = ref([])
const searching = ref(false)

// 搜索基金
let searchTimeout
async function handleSearch(keyword) {
  clearTimeout(searchTimeout)
  if (!keyword || keyword.length < 2) {
    searchResults.value = []
    return
  }
  
  searchTimeout = setTimeout(async () => {
    searching.value = true
    try {
      searchResults.value = await fundStore.searchFunds(keyword)
    } finally {
      searching.value = false
    }
  }, 300)
}

// 快速添加基金
async function quickAddFund(code, name) {
  try {
    await fundStore.addFund({ fund_code: code, fund_name: name })
    searchKeyword.value = ''
    searchResults.value = []
    await fundStore.selectFund(code)
    router.push(`/fund/${code}`)
  } catch (error) {
    console.error('添加失败:', error)
  }
}

// 选择基金
function selectFund(fund) {
  router.push(`/fund/${fund.fund_code}`)
}
</script>

<template>
  <div class="fund-list-container">
    <!-- 持仓汇总卡片 -->
    <div class="summary-card">
      <div class="summary-header">
        <el-icon><Wallet /></el-icon>
        <span>持仓汇总</span>
      </div>
      <div class="summary-body">
        <div class="summary-main">
          <div class="summary-label">总市值</div>
          <div class="summary-value">{{ formatCurrency(fundStore.holdingsSummary.total_market_value) }}</div>
        </div>
        <div class="summary-grid">
          <div class="summary-item">
            <span class="label">投入</span>
            <span class="value">{{ formatCurrency(fundStore.holdingsSummary.total_cost) }}</span>
          </div>
          <div class="summary-item">
            <span class="label">盈亏</span>
            <span class="value" :class="{ profit: fundStore.holdingsSummary.total_profit > 0, loss: fundStore.holdingsSummary.total_profit < 0 }">
              {{ formatCurrency(fundStore.holdingsSummary.total_profit) }}
            </span>
          </div>
          <div class="summary-item">
            <span class="label">当日收益</span>
            <span class="value" :class="{ profit: fundStore.holdingsSummary.today_profit > 0, loss: fundStore.holdingsSummary.today_profit < 0 }">
              {{ (fundStore.holdingsSummary.today_profit > 0 ? '+' : '') + formatCurrency(fundStore.holdingsSummary.today_profit).slice(1) }}
            </span>
          </div>
          <div class="summary-item">
            <span class="label">收益率</span>
            <span class="value" :class="{ profit: fundStore.holdingsSummary.profit_rate > 0, loss: fundStore.holdingsSummary.profit_rate < 0 }">
              {{ formatPercent(fundStore.holdingsSummary.profit_rate) }}
            </span>
          </div>
        </div>
        <!-- AI分析按钮 -->
        <div class="ai-action">
          <el-button 
            type="primary" 
            class="ai-analysis-btn"
            @click="$emit('ai-analysis')"
            :loading="aiLoading"
          >
            <el-icon><MagicStick /></el-icon>
            <span>AI智能分析</span>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 搜索框 -->
    <div class="search-box">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索/添加基金..."
        :prefix-icon="Search"
        clearable
        size="large"
        @input="handleSearch"
      />
      
      <!-- 搜索结果下拉 -->
      <div v-if="searchResults.length > 0" class="search-results">
        <div
          v-for="item in searchResults"
          :key="item.fund_code"
          class="search-item"
          @click="quickAddFund(item.fund_code, item.fund_name)"
        >
          <div class="name">{{ item.fund_name }}</div>
          <div class="code">{{ item.fund_code }} · {{ item.fund_type }}</div>
        </div>
      </div>
    </div>

    <!-- 基金列表 -->
    <div class="fund-list">
      <div class="list-header">
        <span>我的基金</span>
        <el-tag size="small" type="info" round>{{ fundStore.funds.length }}</el-tag>
      </div>
      
      <div class="fund-list-scroll">
        <div
          v-for="fund in fundStore.funds"
          :key="fund.fund_code"
          class="fund-item"
          :class="{ active: $route.params.code === fund.fund_code }"
          @click="selectFund(fund)"
        >
          <div class="fund-main">
            <div class="fund-name">{{ fund.fund_name || '-' }}</div>
            <div class="fund-meta">
              <span class="fund-code">{{ fund.fund_code }}</span>
              <span v-if="fund.last_price_date" class="fund-date">{{ fund.last_price_date }}</span>
            </div>
          </div>
          <div class="fund-growth" :class="{ positive: fund.last_growth_rate > 0, negative: fund.last_growth_rate < 0 }">
            {{ fund.last_growth_rate ? (fund.last_growth_rate > 0 ? '+' : '') + fund.last_growth_rate.toFixed(2) + '%' : '-' }}
          </div>
        </div>
        
        <el-empty v-if="fundStore.funds.length === 0" description="暂无基金" :image-size="60" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.fund-list-container {
  padding: 12px;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 持仓汇总卡片 */
.summary-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 20px;
  color: #1a1a2e;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 6px 20px rgba(0, 0, 0, 0.04);
  border: 1px solid #f0f0f0;
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 12px;
}

.summary-header .el-icon {
  color: #1890ff;
  font-size: 16px;
}

.summary-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.summary-main {
  text-align: center;
  padding: 4px 0;
}

.summary-main .summary-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.summary-main .summary-value {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.summary-grid .summary-item {
  background: #f8fafc;
  border-radius: 8px;
  padding: 8px 6px;
  text-align: center;
  border: 1px solid #f1f5f9;
}

.summary-grid .label {
  font-size: 11px;
  color: #64748b;
  display: block;
  margin-bottom: 3px;
}

.summary-grid .value {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a2e;
}

.summary-grid .value.profit {
  color: #dc2626;
}

.summary-grid .value.loss {
  color: #16a34a;
}

/* AI分析按钮 */
.ai-action {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
}

.ai-analysis-btn {
  width: 100%;
  height: 36px;
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
}

.ai-analysis-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.25);
}

.ai-analysis-btn:active {
  transform: translateY(0);
}

.ai-analysis-btn .el-icon {
  font-size: 14px;
}

/* 搜索框 */
.search-box {
  position: relative;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.search-box :deep(.el-input__wrapper) {
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
  border: 1px solid #e8eaed;
  transition: all 0.2s;
}

.search-box :deep(.el-input__wrapper:hover) {
  background: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border-color: #1890ff;
}

.search-box :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.15);
  border-color: #1890ff;
}

.search-results {
  position: absolute;
  top: calc(100% + 12px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #e8eaed;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  z-index: 10;
  max-height: 320px;
  overflow-y: auto;
}

.search-item {
  padding: 14px 20px;
  cursor: pointer;
  border-bottom: 1px solid #f5f7fa;
  transition: all 0.2s;
}

.search-item:last-child {
  border-bottom: none;
}

.search-item:hover {
  background: #f0f7ff;
}

.search-item .name {
  font-weight: 500;
  font-size: 14px;
}

.search-item .code {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

/* 基金列表 */
.fund-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 4px;
  font-size: 13px;
  color: #909399;
  font-weight: 500;
  flex-shrink: 0;
}

.fund-list-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.fund-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.fund-item:hover {
  background: #f5f7fa;
  border-color: #e8eaed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.fund-item.active {
  background: #f0f9ff;
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.12);
}

.fund-main {
  flex: 1;
  min-width: 0;
}

.fund-name {
  font-weight: 500;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}

.fund-code {
  font-size: 12px;
  color: #909399;
}

.fund-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.fund-date {
  font-size: 11px;
  color: #c0c4cc;
  background: #f5f7fa;
  padding: 1px 4px;
  border-radius: 3px;
}

.fund-growth {
  font-size: 14px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  flex-shrink: 0;
}

.fund-growth.positive {
  color: #dc2626;
  background: rgba(220, 38, 38, 0.1);
}

.fund-growth.negative {
  color: #16a34a;
  background: rgba(22, 163, 74, 0.1);
}
</style>
