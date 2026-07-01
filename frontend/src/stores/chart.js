import { defineStore } from 'pinia'
import { ref } from 'vue'
import { marketAPI, etfAPI, tradeAPI } from '@/api'

export const useChartStore = defineStore('chart', () => {
  const chartData = ref(null)
  const etfData = ref(null)

  async function loadChartData(code, period = '1y') {
    try {
      chartData.value = await marketAPI.getChart(code, period)
    } catch (error) {
      console.error('加载图表数据失败:', error)
    }
  }

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

  async function refreshETFData(etfCode) {
    if (!etfCode) return
    try {
      etfData.value = await etfAPI.getAnalysis(etfCode, true)
    } catch (error) {
      console.error('刷新 ETF 数据失败:', error)
      throw error
    }
  }

  async function loadTradeHistory(fundCode, limit = 100) {
    try {
      return await tradeAPI.getAll(fundCode, limit)
    } catch (e) {
      console.error('加载交易记录失败:', e)
      return []
    }
  }

  async function getRecommendedETF(fundType) {
    try {
      return await etfAPI.getRecommended(fundType)
    } catch (e) {
      console.error('获取推荐 ETF 失败:', e)
      return []
    }
  }

  return { chartData, etfData, loadChartData, loadETFData, refreshETFData, loadTradeHistory, getRecommendedETF }
})
