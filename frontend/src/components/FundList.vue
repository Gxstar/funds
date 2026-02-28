<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useFundStore } from '@/stores/funds'
import { fundAPI } from '@/api'

const router = useRouter()
const fundStore = useFundStore()

const searchKeyword = ref('')
const searchResults = ref([])
const searching = ref(false)

// 格式化货币
function formatCurrency(value) {
  if (value === null || value === undefined) return '¥0.00'
  const num = parseFloat(value)
  return '¥' + Math.abs(num).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 格式化百分比
function formatPercent(value) {
  if (value === null || value === undefined) return '0.00%'
  const num = parseFloat(value)
  const sign = num > 0 ? '+' : ''
  return sign + num.toFixed(2) + '%'
}

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
        </div>
        <div class="profit-bar">
          <div class="profit-label">
            <span>收益率</span>
            <span :class="{ profit: fundStore.holdingsSummary.profit_rate > 0, loss: fundStore.holdingsSummary.profit_rate < 0 }">
              {{ formatPercent(fundStore.holdingsSummary.profit_rate) }}
            </span>
          </div>
          <el-progress 
            :percentage="Math.min(Math.abs(fundStore.holdingsSummary.profit_rate || 0), 100)" 
            :color="fundStore.holdingsSummary.profit_rate >= 0 ? '#f56c6c' : '#67c23a'"
            :stroke-width="6"
            :show-text="false"
          />
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
      
      <el-scrollbar height="calc(100vh - 340px)">
        <div
          v-for="fund in fundStore.funds"
          :key="fund.fund_code"
          class="fund-item"
          :class="{ active: $route.params.code === fund.fund_code }"
          @click="selectFund(fund)"
        >
          <div class="fund-main">
            <div class="fund-name">{{ fund.fund_name || '-' }}</div>
            <div class="fund-code">{{ fund.fund_code }}</div>
          </div>
          <div class="fund-growth" :class="{ positive: fund.last_growth_rate > 0, negative: fund.last_growth_rate < 0 }">
            {{ fund.last_growth_rate ? (fund.last_growth_rate > 0 ? '+' : '') + fund.last_growth_rate.toFixed(2) + '%' : '-' }}
          </div>
        </div>
        
        <el-empty v-if="fundStore.funds.length === 0" description="暂无基金" :image-size="60" />
      </el-scrollbar>
    </div>
  </div>
</template>

<style scoped>
.fund-list-container {
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 持仓汇总卡片 */
.summary-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  color: #fff;
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  opacity: 0.9;
  margin-bottom: 12px;
}

.summary-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.summary-main {
  text-align: center;
  padding: 8px 0;
}

.summary-main .summary-label {
  font-size: 12px;
  opacity: 0.8;
  margin-bottom: 4px;
}

.summary-main .summary-value {
  font-size: 26px;
  font-weight: 700;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.summary-grid .summary-item {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  padding: 10px;
  text-align: center;
}

.summary-grid .label {
  font-size: 11px;
  opacity: 0.8;
  display: block;
  margin-bottom: 4px;
}

.summary-grid .value {
  font-size: 15px;
  font-weight: 600;
}

.summary-grid .value.profit {
  color: #ff9999;
}

.summary-grid .value.loss {
  color: #99ffcc;
}

.profit-bar {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  padding: 10px;
}

.profit-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 8px;
}

.profit-label .profit {
  color: #ff9999;
}

.profit-label .loss {
  color: #99ffcc;
}

/* 搜索框 */
.search-box {
  position: relative;
  margin-bottom: 16px;
}

.search-box :deep(.el-input__wrapper) {
  border-radius: 10px;
  background: #f5f7fa;
  box-shadow: none;
}

.search-box :deep(.el-input__wrapper:hover) {
  background: #eef0f3;
}

.search-results {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  z-index: 10;
  max-height: 280px;
  overflow-y: auto;
}

.search-item {
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.search-item:last-child {
  border-bottom: none;
}

.search-item:hover {
  background: #f5f7fa;
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
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 4px;
  font-size: 13px;
  color: #909399;
  font-weight: 500;
}

.fund-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: all 0.2s;
}

.fund-item:hover {
  background: #f5f7fa;
}

.fund-item.active {
  background: linear-gradient(135deg, #e8f4ff 0%, #f0e8ff 100%);
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

.fund-growth {
  font-size: 14px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  flex-shrink: 0;
}

.fund-growth.positive {
  color: #f56c6c;
  background: #fef0f0;
}

.fund-growth.negative {
  color: #67c23a;
  background: #f0f9eb;
}
</style>
