import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fundAPI, holdingAPI, tradeAPI, marketAPI, etfAPI, aiAPI } from '@/api'

export const useFundStore = defineStore('fund', () => {
  // 状态
  const funds = ref([])
  const currentFund = ref(null)
  const holdingsSummary = ref({
    total_cost: 0,
    total_market_value: 0,
    total_profit: 0,
    profit_rate: 0,
    fund_count: 0
  })
  const loading = ref(false)
  const chartData = ref(null)
  const etfData = ref(null)
  const recentTrades = ref([])
  const aiAnalysis = ref(null)
  const aiLoading = ref(false)
  const aiSettings = ref({
    api_key_configured: false,
    deepseek_base_url: '',
    deepseek_model: 'deepseek-chat',
    total_position_amount: '0'
  })

  // 计算属性
  const hasHoldingFunds = computed(() => 
    funds.value.filter(f => f.total_shares && parseFloat(f.total_shares) > 0)
  )

  // 加载基金列表
  async function loadFunds() {
    loading.value = true
    try {
      const result = await fundAPI.getAll()
      funds.value = result.data || []
    } catch (error) {
      console.error('加载基金列表失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 加载持仓汇总
  async function loadHoldingsSummary() {
    try {
      holdingsSummary.value = await holdingAPI.getSummary()
    } catch (error) {
      console.error('加载持仓汇总失败:', error)
    }
  }

  // 选择基金并加载详情
  async function selectFund(code) {
    loading.value = true
    try {
      const fund = await fundAPI.get(code)
      currentFund.value = fund
      
      // 并行加载图表数据和交易预览
      await Promise.all([
        loadChartData(code, '1y'),
        loadTradePreview(code),
        loadETFData(fund.related_etf)
      ])
      
      return fund
    } catch (error) {
      console.error('加载基金详情失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 加载图表数据
  async function loadChartData(code, period = '1y') {
    try {
      chartData.value = await marketAPI.getChart(code, period)
    } catch (error) {
      console.error('加载图表数据失败:', error)
    }
  }

  // 加载交易预览
  async function loadTradePreview(code) {
    try {
      const result = await tradeAPI.getAll(code, 5)
      recentTrades.value = result.data || []
    } catch (error) {
      console.error('加载交易记录失败:', error)
    }
  }

  // 加载 ETF 数据
  async function loadETFData(etfCode) {
    if (!etfCode) {
      etfData.value = null
      return
    }
    try {
      etfData.value = await etfAPI.getAnalysis(etfCode)
    } catch (error) {
      console.error('加载 ETF 数据失败:', error)
      etfData.value = null
    }
  }

  // 添加基金
  async function addFund(data) {
    try {
      await fundAPI.add(data)
      await loadFunds()
    } catch (error) {
      console.error('添加基金失败:', error)
      throw error
    }
  }

  // 删除基金
  async function deleteFund(code) {
    try {
      await fundAPI.delete(code)
      currentFund.value = null
      await loadFunds()
      await loadHoldingsSummary()
    } catch (error) {
      console.error('删除基金失败:', error)
      throw error
    }
  }

  // 搜索基金
  async function searchFunds(keyword) {
    try {
      const result = await fundAPI.search(keyword)
      return result.data || []
    } catch (error) {
      console.error('搜索基金失败:', error)
      return []
    }
  }

  // 设置关联 ETF
  async function setRelatedETF(code, etfCode) {
    try {
      await fundAPI.update(code, { related_etf: etfCode || null })
      if (currentFund.value?.fund_code === code) {
        currentFund.value.related_etf = etfCode
        await loadETFData(etfCode)
      }
    } catch (error) {
      console.error('设置 ETF 失败:', error)
      throw error
    }
  }

  // 更新持仓
  async function updateHolding(code, data) {
    try {
      await holdingAPI.update(code, data)
      await loadHoldingsSummary()
      if (currentFund.value?.fund_code === code) {
        await selectFund(code)
      }
    } catch (error) {
      console.error('更新持仓失败:', error)
      throw error
    }
  }

  // 添加交易
  async function addTrade(data) {
    try {
      await tradeAPI.add(data)
      await tradeAPI.recalculate(data.fund_code)
      await loadHoldingsSummary()
      if (currentFund.value?.fund_code === data.fund_code) {
        await selectFund(data.fund_code)
      }
    } catch (error) {
      console.error('添加交易失败:', error)
      throw error
    }
  }

  // 更新交易
  async function updateTrade(id, data) {
    try {
      await tradeAPI.update(id, data)
      await tradeAPI.recalculate(data.fund_code)
      if (currentFund.value?.fund_code === data.fund_code) {
        await selectFund(data.fund_code)
      }
    } catch (error) {
      console.error('更新交易失败:', error)
      throw error
    }
  }

  // 删除交易
  async function deleteTrade(id, fundCode) {
    try {
      await tradeAPI.delete(id)
      await tradeAPI.recalculate(fundCode)
      await loadHoldingsSummary()
      if (currentFund.value?.fund_code === fundCode) {
        await selectFund(fundCode)
      }
    } catch (error) {
      console.error('删除交易失败:', error)
      throw error
    }
  }

  // 获取 AI 建议
  async function getAISuggestion(code, forceRefresh = false) {
    aiLoading.value = true
    if (forceRefresh) {
      aiAnalysis.value = null
    }
    try {
      const result = await aiAPI.suggest(code, forceRefresh)
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

  // 清空 AI 分析结果
  function clearAIAnalysis() {
    aiAnalysis.value = null
  }

  // 加载 AI 缓存（只在有缓存时加载，不自动分析）
  async function loadAICache(code) {
    try {
      // 使用 cacheOnly=true，只在有缓存时返回，不会自动分析
      const result = await aiAPI.suggest(code, false, true)
      if (result && !result.error && !result.no_cache) {
        aiAnalysis.value = result
      }
    } catch (error) {
      // 静默失败，不影响页面加载
      console.log('AI缓存加载失败:', error)
    }
  }

  // 刷新所有数据
  async function refreshAll() {
    try {
      await marketAPI.syncAll()
      await loadFunds()
      await loadHoldingsSummary()
      if (currentFund.value) {
        await selectFund(currentFund.value.fund_code)
      }
    } catch (error) {
      console.error('刷新失败:', error)
      throw error
    }
  }

  // 加载 AI 设置
  async function loadAISettings() {
    try {
      const settings = await aiAPI.getSettings()
      aiSettings.value = settings
      return settings
    } catch (error) {
      console.error('加载 AI 设置失败:', error)
    }
  }

  return {
    // 状态
    funds,
    currentFund,
    holdingsSummary,
    loading,
    chartData,
    etfData,
    recentTrades,
    aiAnalysis,
    aiLoading,
    aiSettings,
    // 计算属性
    hasHoldingFunds,
    // 方法
    loadFunds,
    loadHoldingsSummary,
    selectFund,
    loadChartData,
    loadTradePreview,
    loadETFData,
    addFund,
    deleteFund,
    searchFunds,
    setRelatedETF,
    updateHolding,
    addTrade,
    updateTrade,
    deleteTrade,
    getAISuggestion,
    clearAIAnalysis,
    loadAICache,
    refreshAll,
    loadAISettings
  }
})
