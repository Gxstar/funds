import { defineStore } from 'pinia'
import { ref } from 'vue'
import { settingsAPI } from '@/api'

export const useSettingsStore = defineStore('settings', () => {
  const dbConfig = ref({
    type: 'postgresql',
    sqlite: { path: '' },
    postgresql: { host: '', port: '', name: '', user: '' }
  })

  const prompts = ref({
    fund_analysis: { system_prompt: '', user_prompt: '' },
    portfolio_analysis: { system_prompt: '', user_prompt: '' }
  })

  const promptVariables = ref({
    fund_analysis: {},
    portfolio_analysis: {}
  })

  const loading = ref(false)

  async function loadDatabaseConfig() {
    try {
      dbConfig.value = await settingsAPI.getDatabaseConfig()
    } catch (error) {
      console.error('加载数据库配置失败:', error)
    }
  }

  async function saveDatabaseConfig(data) {
    try {
      return await settingsAPI.updateDatabaseConfig(data)
    } catch (error) {
      console.error('保存数据库配置失败:', error)
      throw error
    }
  }

  async function loadPrompts() {
    try {
      const result = await settingsAPI.getPrompts()
      prompts.value = result.prompts || prompts.value
      promptVariables.value = result.variables || promptVariables.value
    } catch (error) {
      console.error('加载提示词配置失败:', error)
    }
  }

  async function savePrompts(data) {
    try {
      await settingsAPI.updatePrompts(data)
      await loadPrompts()
    } catch (error) {
      console.error('保存提示词配置失败:', error)
      throw error
    }
  }

  async function resetPrompts() {
    try {
      const result = await settingsAPI.resetPrompts()
      prompts.value = result.prompts || prompts.value
    } catch (error) {
      console.error('重置提示词失败:', error)
      throw error
    }
  }

  async function loadAllSettings() {
    loading.value = true
    try {
      await Promise.all([
        loadDatabaseConfig(),
        loadPrompts()
      ])
    } finally {
      loading.value = false
    }
  }

  return {
    dbConfig, prompts, promptVariables, loading,
    loadDatabaseConfig, saveDatabaseConfig,
    loadPrompts, savePrompts, resetPrompts,
    loadAllSettings
  }
})
