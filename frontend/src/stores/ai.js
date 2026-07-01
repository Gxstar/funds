import { defineStore } from 'pinia'
import { ref } from 'vue'
import { aiAPI } from '@/api'

export const useAIStore = defineStore('ai', () => {
  const aiAnalysis = ref(null)
  const aiLoading = ref(false)
  const aiSettings = ref({
    api_key_configured: false,
    deepseek_base_url: '',
    deepseek_model: 'deepseek-chat',
    total_position_amount: '0'
  })

  async function loadAISettings() {
    try {
      const settings = await aiAPI.getSettings()
      aiSettings.value = settings
      return settings
    } catch (error) {
      console.error('加载 AI 设置失败:', error)
    }
  }

  async function getAISuggestion(code, forceRefresh = false) {
    aiLoading.value = true
    if (forceRefresh) {
      aiAnalysis.value = null
    }
    try {
      const result = await aiAPI.suggest(code, forceRefresh, false)
      if (result.error) {
        throw new Error(result.error)
      }
      aiAnalysis.value = result
      return result
    } catch (error) {
      console.error('AI 分析失败:', error)
      throw error
    } finally {
      aiLoading.value = false
    }
  }

  function clearAIAnalysis() {
    aiAnalysis.value = null
  }

  async function loadAICache(code) {
    try {
      const result = await aiAPI.suggest(code, false, true)
      if (result && !result.error && !result.no_cache) {
        aiAnalysis.value = result
      } else {
        aiAnalysis.value = null
      }
    } catch (error) {
      console.log('AI缓存加载失败:', error)
    }
  }

  async function analyzePortfolio(forceRefresh = false, cacheOnly = false) {
    aiLoading.value = true
    try {
      const result = await aiAPI.analyze(forceRefresh, cacheOnly)
      aiAnalysis.value = result
      return result
    } catch (e) {
      console.error('AI 组合分析失败:', e)
      throw e
    } finally {
      aiLoading.value = false
    }
  }

  return {
    aiAnalysis, aiLoading, aiSettings,
    loadAISettings, getAISuggestion, clearAIAnalysis, loadAICache,
    analyzePortfolio
  }
})
