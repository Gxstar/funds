<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/funds'
import { aiAPI } from '@/api'
import { formatCurrency, formatPercent, formatDateTime } from '@/utils/format'
import { marked } from 'marked'
import FundList from '@/components/FundList.vue'
import SettingsDrawer from '@/components/SettingsDrawer.vue'
import AddFundDialog from '@/components/AddFundDialog.vue'

const router = useRouter()
const fundStore = useFundStore()

const settingsDrawerVisible = ref(false)
const refreshing = ref(false)
const lastUpdateTime = ref('-')

// AI 分析相关
const portfolioLoading = ref(false)
const portfolioAnalysis = ref(null)
const showAnalysisDialog = ref(false)

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true
})

// 更新最后更新时间
function updateLastUpdateTime() {
  lastUpdateTime.value = new Date().toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(async () => {
  await fundStore.loadFunds()
  await fundStore.loadHoldingsSummary()
  updateLastUpdateTime()
})

// 刷新数据
async function handleRefresh() {
  refreshing.value = true
  try {
    await fundStore.refreshAll()
    updateLastUpdateTime()
    ElMessage.success('数据刷新成功')
  } catch (error) {
    ElMessage.error(error.message || '刷新失败')
  } finally {
    refreshing.value = false
  }
}

// 添加基金成功
function handleFundAdded() {
  ElMessage.success('基金添加成功')
}

// 删除基金
async function handleDeleteFund(code) {
  try {
    await fundStore.deleteFund(code)
    router.push('/')
    ElMessage.success('基金已删除')
  } catch (error) {
    ElMessage.error(error.message || '删除失败')
  }
}

// 渲染 Markdown
function renderMarkdown(text) {
  if (!text) return ''
  return marked(text)
}

// AI 持仓分析 - 加载缓存（优先展示缓存，没有缓存不弹窗）
async function loadPortfolioAnalysis() {
  portfolioLoading.value = true
  try {
    // cacheOnly=true：只获取缓存，没有缓存时返回 no_cache
    const result = await aiAPI.analyze(false, true)
    if (result.no_cache) {
      // 没有缓存，不显示弹窗
      portfolioAnalysis.value = null
    } else {
      portfolioAnalysis.value = result
    }
  } catch (error) {
    console.error('加载分析缓存失败:', error)
  } finally {
    portfolioLoading.value = false
  }
}

// AI 持仓分析 - 刷新分析（强制重新分析并更新数据库）
async function refreshPortfolioAnalysis() {
  portfolioLoading.value = true
  try {
    // forceRefresh=true：强制重新分析，结果会保存到数据库替换旧数据
    const result = await aiAPI.analyze(true, false)
    if (result.error) throw new Error(result.error)
    portfolioAnalysis.value = result
  } catch (error) {
    ElMessage.error(error.message || '分析失败')
  } finally {
    portfolioLoading.value = false
  }
}

// AI 持仓分析 - 打开弹窗
async function openAnalysisDialog() {
  showAnalysisDialog.value = true
  // 先尝试加载缓存
  await loadPortfolioAnalysis()
  // 如果没有缓存，则进行新分析
  if (!portfolioAnalysis.value) {
    await refreshPortfolioAnalysis()
  }
}
</script>

<template>
  <el-container class="app-container">
    <!-- 顶部导航 -->
    <el-header class="app-header">
      <div class="header-left">
        <div class="logo">
          <el-icon :size="22"><TrendCharts /></el-icon>
        </div>
        <span class="app-title">基金管理</span>
      </div>
      <div class="header-right">
        <el-tooltip content="首页" placement="bottom">
          <el-button circle :class="{ active: $route.path === '/' }" @click="router.push('/')">
            <el-icon><HomeFilled /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="添加基金" placement="bottom">
          <el-button circle @click="fundStore.$patch({ showAddDialog: true })">
            <el-icon><Plus /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="刷新数据" placement="bottom">
          <el-button circle :loading="refreshing" @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="设置" placement="bottom">
          <el-button circle @click="settingsDrawerVisible = true">
            <el-icon><Setting /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </el-header>

    <el-container class="main-container">
      <!-- 左侧边栏 -->
      <el-aside width="300px" class="app-aside">
        <FundList 
          :ai-loading="portfolioLoading"
          @ai-analysis="openAnalysisDialog"
        />
      </el-aside>

      <!-- 主内容区 -->
      <el-main class="app-main">
        <router-view 
          @delete-fund="handleDeleteFund"
          @fund-added="handleFundAdded"
        />
      </el-main>
    </el-container>

    <!-- 底部状态栏 -->
    <el-footer class="app-footer">
      <div class="footer-left">
        <el-icon><Clock /></el-icon>
        <span>{{ lastUpdateTime }}</span>
      </div>
      <div class="footer-right">
        <span>数据来源: AkShare</span>
      </div>
    </el-footer>

    <!-- 设置抽屉 -->
    <SettingsDrawer v-model="settingsDrawerVisible" />
    
    <!-- 添加基金对话框 -->
    <AddFundDialog />

    <!-- AI 分析结果弹窗 -->
    <el-dialog v-model="showAnalysisDialog" title="AI 持仓分析报告" width="700px">
      <div v-if="portfolioLoading" class="loading-wrapper">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <span>正在分析您的持仓组合，请稍候...</span>
      </div>
      <div v-else-if="portfolioAnalysis">
        <!-- 分析时间和缓存状态 -->
        <div class="analysis-header">
          <div class="analysis-time">
            <el-icon><Clock /></el-icon>
            <span>分析时间：{{ formatDateTime(portfolioAnalysis.timestamp) }}</span>
          </div>
          <div class="analysis-actions">
            <el-tag v-if="portfolioAnalysis.cached" type="warning" size="small">缓存</el-tag>
            <el-tag v-else type="success" size="small">最新</el-tag>
            <el-button type="primary" size="small" @click="refreshPortfolioAnalysis" :loading="portfolioLoading">
              <el-icon><Refresh /></el-icon>
              刷新分析
            </el-button>
          </div>
        </div>
        <!-- 汇总 -->
        <div class="analysis-summary">
          <div class="summary-item">
            <div class="summary-label">持有基金</div>
            <div class="summary-value">{{ portfolioAnalysis.summary?.fund_count }} 只</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">总投入</div>
            <div class="summary-value">{{ formatCurrency(portfolioAnalysis.summary?.total_cost) }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">总市值</div>
            <div class="summary-value">{{ formatCurrency(portfolioAnalysis.summary?.total_market_value) }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">总盈亏</div>
            <div class="summary-value" :class="{ positive: portfolioAnalysis.summary?.total_profit > 0, negative: portfolioAnalysis.summary?.total_profit < 0 }">
              {{ formatCurrency(portfolioAnalysis.summary?.total_profit) }}
            </div>
          </div>
          <div class="summary-item">
            <div class="summary-label">收益率</div>
            <div class="summary-value" :class="{ positive: portfolioAnalysis.summary?.profit_rate > 0, negative: portfolioAnalysis.summary?.profit_rate < 0 }">
              {{ formatPercent(portfolioAnalysis.summary?.profit_rate) }}
            </div>
          </div>
          <div class="summary-item">
            <div class="summary-label">账户仓位</div>
            <div class="summary-value">{{ portfolioAnalysis.summary?.position_ratio?.toFixed(1) }}%</div>
          </div>
        </div>
        <!-- 分析内容 -->
        <el-scrollbar height="400px" class="analysis-content">
          <div class="markdown-body" v-html="renderMarkdown(portfolioAnalysis.analysis)"></div>
        </el-scrollbar>
      </div>
    </el-dialog>
  </el-container>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
}

/* 顶部导航 */
.app-header {
  background: #fff;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  z-index: 100;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.app-title {
  font-size: 17px;
  font-weight: 600;
  color: #1a1a2e;
}

.header-right {
  display: flex;
  gap: 12px;
}

.header-right .el-button.is-circle {
  width: 40px;
  height: 40px;
  border: none;
  background: #fff;
  color: #606266;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
}

.header-right .el-button.is-circle:hover {
  background: #f0f7ff;
  color: #1890ff;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.15);
  transform: translateY(-1px);
}

.header-right .el-button.is-circle.active {
  background: #1890ff;
  color: #fff;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.25);
}

/* 主容器 */
.main-container {
  flex: 1;
  overflow: hidden;
}

/* 侧边栏 */
.app-aside {
  background: #fff;
  border-right: 1px solid #e8eaed;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.03);
}

/* 主内容区 */
.app-main {
  display: flex;
  background: #f0f2f5;
  padding: 24px;
  overflow-y: auto;
  justify-content: center; /* 水平居中 */
}

/* 底部状态栏 */
.app-footer {
  background: #fff;
  border-top: 1px solid #e8eaed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 32px;
  font-size: 12px;
  color: #909399;
  flex-shrink: 0;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* AI 分析弹窗样式 */
.loading-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  gap: 12px;
  color: #909399;
}

.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.analysis-time {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.analysis-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.analysis-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
  background: #f8fafc;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #f1f5f9;
}

.analysis-summary .summary-item {
  text-align: center;
}

.analysis-summary .summary-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.analysis-summary .summary-value {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.analysis-summary .summary-value.positive {
  color: #dc2626;
}

.analysis-summary .summary-value.negative {
  color: #16a34a;
}

.analysis-content {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
}

.markdown-body {
  line-height: 1.8;
}
</style>