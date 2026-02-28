<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/funds'

const router = useRouter()
const fundStore = useFundStore()

const dialogVisible = ref(false)
const form = ref({
  fund_code: '',
  fund_name: ''
})
const loading = ref(false)

// 监听 store 中的状态
fundStore.$subscribe((mutation, state) => {
  if (state.showAddDialog) {
    dialogVisible.value = true
    form.value = { fund_code: '', fund_name: '' }
    fundStore.showAddDialog = false
  }
})

async function handleSubmit() {
  if (!form.value.fund_code) {
    ElMessage.warning('请输入基金代码')
    return
  }
  
  loading.value = true
  try {
    const code = await fundStore.addFund(form.value)
    dialogVisible.value = false
    ElMessage.success('基金添加成功')
    router.push(`/fund/${code}`)
  } catch (error) {
    ElMessage.error(error.message || '添加失败')
  } finally {
    loading.value = false
  }
}

function handleOpen() {
  form.value = { fund_code: '', fund_name: '' }
}

function handleClosed() {
  fundStore.showAddDialog = false
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="添加基金"
    width="450px"
    @open="handleOpen"
    @closed="handleClosed"
  >
    <el-form label-width="80px">
      <el-form-item label="基金代码">
        <el-input v-model="form.fund_code" placeholder="请输入6位基金代码" maxlength="6" />
      </el-form-item>
      <el-form-item label="基金名称">
        <el-input v-model="form.fund_name" placeholder="自动获取或手动输入" />
      </el-form-item>
    </el-form>
    
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">确认添加</el-button>
    </template>
  </el-dialog>
</template>
