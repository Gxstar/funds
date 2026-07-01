import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fundAPI, marketAPI, holdingAPI, tradeAPI } from '@/api'
import { useChartStore } from '@/stores/chart'
import { useHoldingStore } from '@/stores/holdings'

export const useFundStore = defineStore('fund', () => {
  const funds = ref([])
  const currentFund = ref(null)
  const loading = ref(false)
  const showAddDialog = ref(false)

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

  async function selectFund(code) {
    loading.value = true
    try {
      try {
        await marketAPI.sync(code)
      } catch (syncErr) {
        console.log('同步净值失败，使用缓存数据:', syncErr)
      }

      const fund = await fundAPI.get(code)
      currentFund.value = fund

      const chartStore = useChartStore()
      const holdingStore = useHoldingStore()
      await Promise.all([
        chartStore.loadChartData(code, '1y'),
        holdingStore.loadTradePreview(code),
        chartStore.loadETFData(fund.related_etf)
      ])

      return fund
    } catch (error) {
      console.error('加载基金详情失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function addFund(data) {
    try {
      await fundAPI.add(data)
      await loadFunds()
      return data.fund_code
    } catch (error) {
      console.error('添加基金失败:', error)
      throw error
    }
  }

  async function deleteFund(code) {
    try {
      await fundAPI.delete(code)
      currentFund.value = null
      await loadFunds()
      await useHoldingStore().loadHoldingsSummary()
    } catch (error) {
      console.error('删除基金失败:', error)
      throw error
    }
  }

  async function searchFunds(keyword) {
    try {
      const result = await fundAPI.search(keyword)
      return result.data || []
    } catch (error) {
      console.error('搜索基金失败:', error)
      return []
    }
  }

  async function setRelatedETF(code, etfCode) {
    try {
      await fundAPI.update(code, { related_etf: etfCode || null })
      if (currentFund.value?.fund_code === code) {
        currentFund.value.related_etf = etfCode
        await useChartStore().loadETFData(etfCode)
      }
    } catch (error) {
      console.error('设置 ETF 失败:', error)
      throw error
    }
  }

  async function updateHolding(code, data) {
    try {
      await holdingAPI.update(code, data)
      await useHoldingStore().loadHoldingsSummary()
      if (currentFund.value?.fund_code === code) {
        await selectFund(code)
      }
    } catch (error) {
      console.error('更新持仓失败:', error)
      throw error
    }
  }

  async function addTrade(data) {
    try {
      await tradeAPI.add(data)
      await tradeAPI.recalculate(data.fund_code)
      await useHoldingStore().loadHoldingsSummary()
      if (currentFund.value?.fund_code === data.fund_code) {
        await selectFund(data.fund_code)
      }
    } catch (error) {
      console.error('添加交易失败:', error)
      throw error
    }
  }

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

  async function deleteTrade(id, fundCode) {
    try {
      await tradeAPI.delete(id)
      await tradeAPI.recalculate(fundCode)
      await useHoldingStore().loadHoldingsSummary()
      if (currentFund.value?.fund_code === fundCode) {
        await selectFund(fundCode)
      }
    } catch (error) {
      console.error('删除交易失败:', error)
      throw error
    }
  }

  async function syncAll() {
    try {
      return await marketAPI.syncAll()
    } catch (e) {
      console.error('全量同步失败:', e)
      throw e
    }
  }

  async function syncFundData(code) {
    try {
      return await marketAPI.sync(code)
    } catch (e) {
      console.error('同步基金数据失败:', e)
      throw e
    }
  }

  async function loadIndices(skipCache = false) {
    try {
      return await marketAPI.getIndices(skipCache)
    } catch (e) {
      console.error('加载市场指数失败:', e)
      return { data: [], date: '', is_today: true, update_time: '' }
    }
  }

  async function refreshAll() {
    try {
      await syncAll()

      for (const fund of funds.value) {
        try {
          await fundAPI.refreshInfo(fund.fund_code)
        } catch (e) {
          console.log(`刷新基金 ${fund.fund_code} 信息失败:`, e)
        }
      }

      await loadFunds()
      await useHoldingStore().loadHoldingsSummary()
      if (currentFund.value) {
        await selectFund(currentFund.value.fund_code)
      }
    } catch (error) {
      console.error('刷新失败:', error)
      throw error
    }
  }

  return {
    funds, currentFund, loading, showAddDialog,
    loadFunds, selectFund, addFund, deleteFund, searchFunds,
    setRelatedETF, updateHolding, addTrade, updateTrade, deleteTrade,
    refreshAll, syncAll, syncFundData, loadIndices
  }
})
