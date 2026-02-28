import { defineStore } from 'pinia'
import { ref } from 'vue'
import { aiAPI, settingsAPI } from '@/api'

export const useSettingsStore = defineStore('settings', () => {
  // 状态
  const aiSettings = ref({
    api_key_configured: false,
    deepseek_api_key: '',
    deepseek_base_url: '',
    deepseek_model: 'deepseek-chat',
    total_position_amount: '0'
  })
  
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

  // 加载 AI 设置
  async function loadAISettings() {
    try {
      const settings = await aiAPI.getSettings()
      aiSettings.value = settings
    } catch (error) {
      console.error('加载 AI 设置失败:', error)
    }
  }

  // 保存 AI 设置
  async function saveAISettings(data) {
    try {
      await aiAPI.updateSettings(data)
      await loadAISettings()
    } catch (error) {
      console.error('保存 AI 设置失败:', error)
      throw error
    }
  }

  // 保存仓位设置
  async function savePositionSetting(amount) {
    try {
      await aiAPI.updatePositionSetting({ total_position_amount: amount })
      aiSettings.value.total_position_amount = amount || '0'
    } catch (error) {
      console.error('保存仓位设置失败:', error)
      throw error
    }
  }

  // 加载数据库配置
  async function loadDatabaseConfig() {
    try {
      dbConfig.value = await settingsAPI.getDatabaseConfig()
    } catch (error) {
      console.error('加载数据库配置失败:', error)
    }
  }

  // 保存数据库配置
  async function saveDatabaseConfig(data) {
    try {
      return await settingsAPI.updateDatabaseConfig(data)
    } catch (error) {
      console.error('保存数据库配置失败:', error)
      throw error
    }
  }

  // 加载提示词配置
  async function loadPrompts() {
    try {
      const result = await settingsAPI.getPrompts()
      prompts.value = result.prompts || prompts.value
      promptVariables.value = result.variables || promptVariables.value
    } catch (error) {
      console.error('加载提示词配置失败:', error)
    }
  }

  // 保存提示词配置
  async function savePrompts(data) {
    try {
      await settingsAPI.updatePrompts(data)
      await loadPrompts()
    } catch (error) {
      console.error('保存提示词配置失败:', error)
      throw error
    }
  }

  // 重置提示词
  async function resetPrompts() {
    try {
      const result = await settingsAPI.resetPrompts()
      prompts.value = result.prompts || prompts.value
    } catch (error) {
      console.error('重置提示词失败:', error)
      throw error
    }
  }

  // 加载所有设置
  async function loadAllSettings() {
    loading.value = true
    try {
      await Promise.all([
        loadAISettings(),
        loadDatabaseConfig(),
        loadPrompts()
      ])
    } finally {
      loading.value = false
    }
  }

  return {
    // 状态
    aiSettings,
    dbConfig,
    prompts,
    promptVariables,
    loading,
    // 方法
    loadAISettings,
    saveAISettings,
    savePositionSetting,
    loadDatabaseConfig,
    saveDatabaseConfig,
    loadPrompts,
    savePrompts,
    resetPrompts,
    loadAllSettings
  }
})
