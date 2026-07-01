import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { holdingAPI, tradeAPI, marketAPI } from '@/api'
import { useFundStore } from '@/stores/funds'

export const useHoldingStore = defineStore('holding', () => {
  const holdingsSummary = ref({
    total_cost: 0,
    total_market_value: 0,
    total_profit: 0,
    profit_rate: 0,
    today_profit: 0,
    fund_count: 0
  })
  const recentTrades = ref([])

  const holdingFunds = computed(() => {
    const fundStore = useFundStore()
    return fundStore.funds.filter(f => f.total_shares && parseFloat(f.total_shares) > 0)
  })

  async function loadHoldingsSummary() {
    try {
      holdingsSummary.value = await holdingAPI.getSummary()
    } catch (error) {
      console.error('加载持仓汇总失败:', error)
    }
  }

  async function loadTradePreview(code) {
    try {
      const result = await tradeAPI.getAll(code, 5)
      recentTrades.value = result.data || []
    } catch (error) {
      console.error('加载交易记录失败:', error)
    }
  }

  async function loadRecentTrades(limit = 10) {
    try {
      const result = await tradeAPI.getAll(null, limit)
      recentTrades.value = result.data || []
    } catch (error) {
      console.error('加载近期交易失败:', error)
    }
  }

  async function loadPortfolioHistory(days = 90) {
    try {
      return await holdingAPI.getPortfolioHistory(days)
    } catch (e) {
      console.error('加载组合历史失败:', e)
      return []
    }
  }

  return {
    holdingsSummary, recentTrades, holdingFunds,
    loadHoldingsSummary, loadTradePreview, loadRecentTrades,
    loadPortfolioHistory
  }
})
