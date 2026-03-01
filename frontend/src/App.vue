<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/funds'
import FundList from '@/components/FundList.vue'
import SettingsDrawer from '@/components/SettingsDrawer.vue'
import AddFundDialog from '@/components/AddFundDialog.vue'

const router = useRouter()
const fundStore = useFundStore()

const settingsDrawerVisible = ref(false)
const refreshing = ref(false)
const lastUpdateTime = ref('-')

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
        <FundList />
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
  padding: 0 20px;
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
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
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
  gap: 8px;
}

.header-right .el-button.is-circle {
  width: 36px;
  height: 36px;
  border: none;
  background: #f5f7fa;
  color: #606266;
}

.header-right .el-button.is-circle:hover {
  background: #e8eaed;
  color: #409eff;
}

.header-right .el-button.is-circle.active {
  background: #e8f4ff;
  color: #409eff;
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
}

/* 主内容区 */
.app-main {
  display: flex;
  background: #f0f2f5;
  padding: 20px;
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
  padding: 0 20px;
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
</style>