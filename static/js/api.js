/** API 封装 */

const API_BASE = '/api';

// 通用请求方法
async function request(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    if (mergedOptions.body && typeof mergedOptions.body === 'object') {
        mergedOptions.body = JSON.stringify(mergedOptions.body);
    }
    
    const response = await fetch(url, mergedOptions);
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: '请求失败' }));
        throw new Error(error.detail || '请求失败');
    }
    
    return response.json();
}

// 基金相关 API
const fundAPI = {
    // 获取所有基金
    getAll: () => request(`${API_BASE}/funds`),
    
    // 获取单个基金
    get: (code) => request(`${API_BASE}/funds/${code}`),
    
    // 添加基金
    add: (data) => request(`${API_BASE}/funds`, {
        method: 'POST',
        body: data,
    }),
    
    // 更新基金
    update: (code, data) => request(`${API_BASE}/funds/${code}`, {
        method: 'PUT',
        body: data,
    }),
    
    // 删除基金
    delete: (code) => request(`${API_BASE}/funds/${code}`, {
        method: 'DELETE',
    }),
    
    // 搜索基金
    search: (keyword) => request(`${API_BASE}/funds/search/${encodeURIComponent(keyword)}`),
};

// 持仓相关 API
const holdingAPI = {
    // 获取所有持仓
    getAll: () => request(`${API_BASE}/holdings`),
    
    // 获取持仓汇总
    getSummary: () => request(`${API_BASE}/holdings/summary`),
    
    // 获取单只基金持仓
    get: (code) => request(`${API_BASE}/holdings/${code}`),
    
    // 更新持仓
    update: (code, data) => request(`${API_BASE}/holdings/${code}`, {
        method: 'PUT',
        body: data,
    }),
    
    // 删除持仓
    delete: (code) => request(`${API_BASE}/holdings/${code}`, {
        method: 'DELETE',
    }),
    
    // 重新计算持仓
    recalculate: (code) => request(`${API_BASE}/holdings/${code}/recalculate`, {
        method: 'POST',
    }),
};

// 交易相关 API
const tradeAPI = {
    // 获取交易记录
    getAll: (fundCode = null, limit = 100, offset = 0) => {
        let url = `${API_BASE}/trades?limit=${limit}&offset=${offset}`;
        if (fundCode) {
            url = `${API_BASE}/trades?fund_code=${fundCode}&limit=${limit}&offset=${offset}`;
        }
        return request(url);
    },
    
    // 添加交易
    add: (data) => request(`${API_BASE}/trades`, {
        method: 'POST',
        body: data,
    }),
    
    // 更新交易
    update: (id, data) => request(`${API_BASE}/trades/${id}`, {
        method: 'PUT',
        body: data,
    }),
    
    // 删除交易
    delete: (id) => request(`${API_BASE}/trades/${id}`, {
        method: 'DELETE',
    }),
    
    // 重新计算持仓
    recalculate: (code) => request(`${API_BASE}/trades/${code}/recalculate`, {
        method: 'POST',
    }),
};

// 行情相关 API
const marketAPI = {
    // 获取基金信息
    getInfo: (code) => request(`${API_BASE}/market/${code}`),
    
    // 获取历史净值
    getHistory: (code, startDate = null, endDate = null) => {
        let url = `${API_BASE}/market/${code}/history`;
        const params = [];
        if (startDate) params.push(`start_date=${startDate}`);
        if (endDate) params.push(`end_date=${endDate}`);
        if (params.length) url += '?' + params.join('&');
        return request(url);
    },
    
    // 获取图表数据
    getChart: (code, period = '1m') => request(`${API_BASE}/market/${code}/chart?period=${period}`),
    
    // 同步基金数据
    sync: (code, force = false) => request(`${API_BASE}/market/${code}/sync?force=${force}`, {
        method: 'POST',
    }),
    
    // 同步所有基金
    syncAll: () => request(`${API_BASE}/market/sync-all`, {
        method: 'POST',
    }),
};

// AI 相关 API
const aiAPI = {
    // 获取配置状态
    getStatus: () => request(`${API_BASE}/ai/status`),
    
    // 获取建议
    suggest: (code) => request(`${API_BASE}/ai/suggest/${code}`, {
        method: 'POST',
    }),
    
    // 分析持仓组合
    analyze: () => request(`${API_BASE}/ai/analyze`, {
        method: 'POST',
    }),
    
    // 获取设置
    getSettings: () => request(`${API_BASE}/ai/settings`),
    
    // 更新设置
    updateSettings: (data) => request(`${API_BASE}/ai/settings`, {
        method: 'POST',
        body: data,
    }),
    
    // 获取仓位设置
    getPositionSetting: () => request(`${API_BASE}/ai/position-setting`),
    
    // 更新仓位设置
    updatePositionSetting: (data) => request(`${API_BASE}/ai/position-setting`, {
        method: 'POST',
        body: data,
    }),
};

// ETF 相关 API
const etfAPI = {
    // 获取 ETF 实时行情
    getRealtime: (code) => request(`${API_BASE}/etf/realtime/${code}`),
    
    // 获取 ETF 资金流向
    getMoneyFlow: (code) => request(`${API_BASE}/etf/money-flow/${code}`),
    
    // 获取 ETF 分析数据
    getAnalysis: (code) => request(`${API_BASE}/etf/analysis/${code}`),
    
    // 获取推荐 ETF
    getRecommended: (fundType) => request(`${API_BASE}/etf/recommend/${encodeURIComponent(fundType)}`),
    
    // 获取基金关联 ETF 数据
    getFundETF: (fundCode) => request(`${API_BASE}/etf/fund/${fundCode}`),
};

// 设置相关 API
const settingsAPI = {
    // 获取提示词配置
    getPrompts: () => request(`${API_BASE}/ai/prompts`),
    
    // 更新提示词配置
    updatePrompts: (data) => request(`${API_BASE}/ai/prompts`, {
        method: 'POST',
        body: data,
    }),
    
    // 重置提示词配置
    resetPrompts: () => request(`${API_BASE}/ai/prompts/reset`, {
        method: 'POST',
    }),
    
    // 获取数据库配置
    getDatabaseConfig: () => request(`${API_BASE}/ai/database-config`),
    
    // 更新数据库配置
    updateDatabaseConfig: (data) => request(`${API_BASE}/ai/database-config`, {
        method: 'POST',
        body: data,
    }),
};
