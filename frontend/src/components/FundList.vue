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
    <el-card class="summary-card" shadow="never">
      <template #header>
        <span>持仓汇总</span>
      </template>
      <div class="summary-item">
        <span class="label">总投入</span>
        <span class="value">{{ formatCurrency(fundStore.holdingsSummary.total_cost) }}</span>
      </div>
      <div class="summary-item">
        <span class="label">总市值</span>
        <span class="value">{{ formatCurrency(fundStore.holdingsSummary.total_market_value) }}</span>
      </div>
      <div class="summary-item">
        <span class="label">总盈亏</span>
        <span class="value" :class="{ profit: fundStore.holdingsSummary.total_profit > 0, loss: fundStore.holdingsSummary.total_profit < 0 }">
          {{ formatCurrency(fundStore.holdingsSummary.total_profit) }}
        </span>
      </div>
      <div class="summary-item">
        <span class="label">盈亏比</span>
        <span class="value" :class="{ profit: fundStore.holdingsSummary.profit_rate > 0, loss: fundStore.holdingsSummary.profit_rate < 0 }">
          {{ formatPercent(fundStore.holdingsSummary.profit_rate) }}
        </span>
      </div>
    </el-card>

    <!-- 搜索框 -->
    <div class="search-box">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索/添加基金..."
        :suffix-icon="Search"
        clearable
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
          <div class="code">{{ item.fund_code }} {{ item.fund_type }}</div>
        </div>
      </div>
    </div>

    <!-- 基金列表 -->
    <div class="fund-list">
      <div class="list-header">
        <span>我的基金</span>
        <span>({{ fundStore.funds.length }})</span>
      </div>
      
      <el-scrollbar height="calc(100vh - 380px)">
        <div
          v-for="fund in fundStore.funds"
          :key="fund.fund_code"
          class="fund-item"
          :class="{ active: $route.params.code === fund.fund_code }"
          @click="selectFund(fund)"
        >
          <div class="fund-name">{{ fund.fund_name || '-' }}</div>
          <div class="fund-info">
            <span class="code">{{ fund.fund_code }}</span>
            <span
              class="growth"
              :class="{ positive: fund.last_growth_rate > 0, negative: fund.last_growth_rate < 0 }"
            >
              {{ fund.last_growth_rate ? (fund.last_growth_rate > 0 ? '+' : '') + fund.last_growth_rate.toFixed(2) + '%' : '-' }}
            </span>
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
}

.summary-card {
  margin-bottom: 16px;
  background: linear-gradient(135deg, #4f7cff 0%, #7c3aed 100%);
  color: #fff;
}

.summary-card :deep(.el-card__header) {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
}

.summary-card :deep(.el-card__body) {
  padding: 12px 16px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 13px;
}

.summary-item .label {
  opacity: 0.8;
}

.summary-item .value {
  font-weight: 600;
}

.summary-item .value.profit {
  color: #ff6b6b;
}

.summary-item .value.loss {
  color: #20c997;
}

.search-box {
  position: relative;
  margin-bottom: 16px;
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 10;
  max-height: 300px;
  overflow-y: auto;
}

.search-item {
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
}

.search-item:last-child {
  border-bottom: none;
}

.search-item:hover {
  background: #f5f7fa;
}

.search-item .name {
  font-weight: 500;
}

.search-item .code {
  font-size: 12px;
  color: #909399;
}

.fund-list {
  margin-top: 8px;
}

.list-header {
  padding: 8px 0;
  font-size: 13px;
  color: #909399;
  border-bottom: 1px solid #e4e7ed;
  margin-bottom: 8px;
}

.fund-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
}

.fund-item:hover {
  background: #f5f7fa;
}

.fund-item.active {
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
}

.fund-name {
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fund-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
}

.growth {
  font-weight: 500;
}

.growth.positive {
  color: #f56c6c;
}

.growth.negative {
  color: #67c23a;
}
</style>
