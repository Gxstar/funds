<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/funds'
import FundList from '@/components/FundList.vue'
import SettingsDrawer from '@/components/SettingsDrawer.vue'

const router = useRouter()
const fundStore = useFundStore()

const settingsDrawerVisible = ref(false)
const refreshing = ref(false)

onMounted(async () => {
  await fundStore.loadFunds()
  await fundStore.loadHoldingsSummary()
})

// 刷新数据
async function handleRefresh() {
  refreshing.value = true
  try {
    await fundStore.refreshAll()
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
        <el-icon :size="24"><TrendCharts /></el-icon>
        <span class="app-title">基金投资管理工具</span>
      </div>
      <div class="header-right">
        <el-button @click="router.push('/')">
          <el-icon><HomeFilled /></el-icon>
          首页
        </el-button>
        <el-button type="primary" @click="fundStore.$patch({ showAddDialog: true })">
          <el-icon><Plus /></el-icon>
          添加基金
        </el-button>
        <el-button @click="handleRefresh" :loading="refreshing">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button @click="settingsDrawerVisible = true">
          <el-icon><Setting /></el-icon>
          设置
        </el-button>
      </div>
    </el-header>

    <el-container>
      <!-- 左侧边栏 -->
      <el-aside width="280px" class="app-aside">
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
}

.app-container {
  height: 100vh;
}

.app-header {
  background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #fff;
}

.app-title {
  font-size: 18px;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 10px;
}

.app-aside {
  background: #fff;
  border-right: 1px solid #e4e7ed;
  overflow: hidden;
}

.app-main {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>