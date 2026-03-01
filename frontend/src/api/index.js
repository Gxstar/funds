/** API 服务层 */

const API_BASE = '/api'

// 通用请求方法
async function request(url, options = {}) {
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
    },
  }
  
  const mergedOptions = { ...defaultOptions, ...options }
  if (mergedOptions.body && typeof mergedOptions.body === 'object') {
    mergedOptions.body = JSON.stringify(mergedOptions.body)
  }
  
  const response = await fetch(url, mergedOptions)
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '请求失败' }))
    throw new Error(error.detail || '请求失败')
  }
  
  return response.json()
}

// 基金相关 API
export const fundAPI = {
  getAll: () => request(`${API_BASE}/funds`),
  get: (code) => request(`${API_BASE}/funds/${code}`),
  add: (data) => request(`${API_BASE}/funds`, { method: 'POST', body: data }),
  update: (code, data) => request(`${API_BASE}/funds/${code}`, { method: 'PUT', body: data }),
  delete: (code) => request(`${API_BASE}/funds/${code}`, { method: 'DELETE' }),
  search: (keyword) => request(`${API_BASE}/funds/search/${encodeURIComponent(keyword)}`),
}

// 持仓相关 API
export const holdingAPI = {
  getAll: () => request(`${API_BASE}/holdings`),
  getSummary: () => request(`${API_BASE}/holdings/summary`),
  get: (code) => request(`${API_BASE}/holdings/${code}`),
  update: (code, data) => request(`${API_BASE}/holdings/${code}`, { method: 'PUT', body: data }),
  delete: (code) => request(`${API_BASE}/holdings/${code}`, { method: 'DELETE' }),
  recalculate: (code) => request(`${API_BASE}/holdings/${code}/recalculate`, { method: 'POST' }),
}

// 交易相关 API
export const tradeAPI = {
  getAll: (fundCode = null, limit = 100, offset = 0) => {
    let url = `${API_BASE}/trades?limit=${limit}&offset=${offset}`
    if (fundCode) {
      url = `${API_BASE}/trades?fund_code=${fundCode}&limit=${limit}&offset=${offset}`
    }
    return request(url)
  },
  add: (data) => request(`${API_BASE}/trades`, { method: 'POST', body: data }),
  update: (id, data) => request(`${API_BASE}/trades/${id}`, { method: 'PUT', body: data }),
  delete: (id) => request(`${API_BASE}/trades/${id}`, { method: 'DELETE' }),
  recalculate: (code) => request(`${API_BASE}/trades/${code}/recalculate`, { method: 'POST' }),
}

// 行情相关 API
export const marketAPI = {
  getInfo: (code) => request(`${API_BASE}/market/${code}`),
  getHistory: (code, startDate = null, endDate = null) => {
    let url = `${API_BASE}/market/${code}/history`
    const params = []
    if (startDate) params.push(`start_date=${startDate}`)
    if (endDate) params.push(`end_date=${endDate}`)
    if (params.length) url += '?' + params.join('&')
    return request(url)
  },
  getChart: (code, period = '1m') => request(`${API_BASE}/market/${code}/chart?period=${period}`),
  sync: (code, force = false) => request(`${API_BASE}/market/${code}/sync?force=${force}`, { method: 'POST' }),
  syncAll: () => request(`${API_BASE}/market/sync-all`, { method: 'POST' }),
  getIndices: () => request(`${API_BASE}/market/indices`),
}

// AI 相关 API
export const aiAPI = {
  getStatus: () => request(`${API_BASE}/ai/status`),
  suggest: (code, forceRefresh = false, cacheOnly = false) => {
    const params = []
    if (forceRefresh) params.push('force_refresh=true')
    if (cacheOnly) params.push('cache_only=true')
    const queryString = params.length > 0 ? `?${params.join('&')}` : ''
    return request(`${API_BASE}/ai/suggest/${code}${queryString}`, { method: 'POST' })
  },
  getCacheStatus: (code) => request(`${API_BASE}/ai/suggest/${code}/cache`),
  clearCache: (code) => request(`${API_BASE}/ai/suggest/${code}/cache`, { method: 'DELETE' }),
  analyze: (forceRefresh = false, cacheOnly = false) => {
    const params = []
    if (forceRefresh) params.push('force_refresh=true')
    if (cacheOnly) params.push('cache_only=true')
    const queryString = params.length > 0 ? `?${params.join('&')}` : ''
    return request(`${API_BASE}/ai/analyze${queryString}`, { method: 'POST' })
  },
  getAnalyzeCache: () => request(`${API_BASE}/ai/analyze/cache`),
  clearAnalyzeCache: () => request(`${API_BASE}/ai/analyze/cache`, { method: 'DELETE' }),
  getSettings: () => request(`${API_BASE}/ai/settings`),
  updateSettings: (data) => request(`${API_BASE}/ai/settings`, { method: 'POST', body: data }),
  getPositionSetting: () => request(`${API_BASE}/ai/position-setting`),
  updatePositionSetting: (data) => request(`${API_BASE}/ai/position-setting`, { method: 'POST', body: data }),
}

// 设置相关 API
export const settingsAPI = {
  getPrompts: () => request(`${API_BASE}/ai/prompts`),
  updatePrompts: (data) => request(`${API_BASE}/ai/prompts`, { method: 'POST', body: data }),
  resetPrompts: () => request(`${API_BASE}/ai/prompts/reset`, { method: 'POST' }),
  getDatabaseConfig: () => request(`${API_BASE}/ai/database-config`),
  updateDatabaseConfig: (data) => request(`${API_BASE}/ai/database-config`, { method: 'POST', body: data }),
}

// ETF 相关 API
export const etfAPI = {
  getRealtime: (code) => request(`${API_BASE}/etf/realtime/${code}`),
  getMoneyFlow: (code) => request(`${API_BASE}/etf/money-flow/${code}`),
  getAnalysis: (code) => request(`${API_BASE}/etf/analysis/${code}`),
  getRecommended: (fundType) => request(`${API_BASE}/etf/recommend/${encodeURIComponent(fundType)}`),
  getFundETF: (fundCode) => request(`${API_BASE}/etf/fund/${fundCode}`),
}
