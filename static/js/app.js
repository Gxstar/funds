/** 主应用程序 */

let currentFundCode = null;
let chart = null;
let currentPeriod = '1y';

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    initChart();
    bindEvents();
});

function initApp() {
    loadFundList();
    loadHoldingsSummary();
}

function bindEvents() {
    // 时间范围选择器
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentPeriod = e.target.dataset.period;
            if (currentFundCode) {
                loadChart(currentFundCode, currentPeriod);
            }
        });
    });
}

// 加载基金列表
async function loadFundList() {
    try {
        const result = await fundAPI.getAll();
        const funds = result.data || [];
        
        const container = document.getElementById('fund-list-items');
        document.getElementById('fund-count').textContent = `(${funds.length})`;
        
        if (funds.length === 0) {
            container.innerHTML = '<div class="no-data" style="padding: 20px; text-align: center; color: #999;">暂无基金，点击上方添加</div>';
            return;
        }
        
        container.innerHTML = funds.map(fund => {
            const growthRate = fund.last_growth_rate;
            const growthClass = growthRate > 0 ? 'positive' : growthRate < 0 ? 'negative' : '';
            const growthText = growthRate ? `${growthRate > 0 ? '+' : ''}${growthRate.toFixed(2)}%` : '-';
            
            return `
                <div class="fund-item ${fund.fund_code === currentFundCode ? 'active' : ''}" 
                     onclick="selectFund('${fund.fund_code}')">
                    <div class="name">${fund.fund_name || '-'}</div>
                    <div class="info">
                        <span class="code">${fund.fund_code}</span>
                        <span class="growth ${growthClass}">${growthText}</span>
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('加载基金列表失败:', error);
    }
}

// 加载持仓汇总
async function loadHoldingsSummary() {
    try {
        const summary = await holdingAPI.getSummary();
        
        document.getElementById('total-cost').textContent = formatCurrency(summary.total_cost);
        document.getElementById('total-market').textContent = formatCurrency(summary.total_market_value);
        
        const profitEl = document.getElementById('total-profit');
        const profitRateEl = document.getElementById('profit-rate');
        
        profitEl.textContent = formatCurrency(summary.total_profit);
        profitRateEl.textContent = formatPercent(summary.profit_rate);
        
        // 先移除旧的颜色类
        profitEl.classList.remove('text-red', 'text-green');
        profitRateEl.classList.remove('text-red', 'text-green');
        
        if (summary.total_profit > 0) {
            profitEl.classList.add('text-red');
            profitRateEl.classList.add('text-red');
        } else if (summary.total_profit < 0) {
            profitEl.classList.add('text-green');
            profitRateEl.classList.add('text-green');
        }
        
    } catch (error) {
        console.error('加载持仓汇总失败:', error);
    }
}

// 选择基金
async function selectFund(fundCode) {
    currentFundCode = fundCode;
    
    // 更新列表选中状态
    document.querySelectorAll('.fund-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget?.classList.add('active');
    
    // 显示详情区域
    document.getElementById('no-selection').style.display = 'none';
    document.getElementById('fund-detail').style.display = 'block';
    
    // 加载基金详情
    await loadFundDetail(fundCode);
    await loadChart(fundCode, currentPeriod);
    
    // 确保 ECharts 正确渲染（容器从隐藏变为显示后需要 resize）
    setTimeout(() => {
        if (chart) {
            chart.resize();
        }
    }, 100);
    
    await loadTradePreview(fundCode);
}

// 加载基金详情
async function loadFundDetail(fundCode) {
    try {
        const fund = await fundAPI.get(fundCode);
        
        // 基本信息
        document.getElementById('fund-name').textContent = fund.fund_name || '-';
        document.getElementById('fund-code').textContent = fund.fund_code;
        document.getElementById('fund-type').textContent = fund.fund_type || '-';
        document.getElementById('risk-level').textContent = fund.risk_level || '-';
        document.getElementById('current-value').textContent = fund.last_net_value ? fund.last_net_value.toFixed(4) : '-';
        
        const growthEl = document.getElementById('growth-rate');
        if (fund.last_growth_rate !== null && fund.last_growth_rate !== undefined) {
            growthEl.textContent = formatPercent(fund.last_growth_rate);
            growthEl.className = 'value ' + (fund.last_growth_rate > 0 ? 'text-red' : fund.last_growth_rate < 0 ? 'text-green' : '');
        } else {
            growthEl.textContent = '-';
            growthEl.className = 'value';
        }
        
        // 持仓信息 - 始终显示卡片
        const noHoldingEl = document.getElementById('no-holding');
        const hasHoldingEl = document.getElementById('has-holding');
        const sellBtn = document.getElementById('sell-btn');
        
        if (fund.total_shares && parseFloat(fund.total_shares) > 0) {
            // 有持仓
            noHoldingEl.style.display = 'none';
            hasHoldingEl.style.display = 'block';
            sellBtn.style.display = 'inline-flex';
            
            const shares = parseFloat(fund.total_shares);
            const costPrice = parseFloat(fund.cost_price);
            const totalCost = parseFloat(fund.total_cost);
            const currentValue = fund.last_net_value ? parseFloat(fund.last_net_value) : 0;
            const marketValue = shares * currentValue;
            const profit = marketValue - totalCost;
            const profitRatio = totalCost ? (profit / totalCost * 100) : 0;
            
            document.getElementById('shares').textContent = shares.toFixed(2);
            document.getElementById('cost-price').textContent = costPrice.toFixed(4);
            document.getElementById('market-value').textContent = formatCurrency(marketValue);
            
            const profitEl = document.getElementById('profit');
            const profitRatioEl = document.getElementById('profit-ratio');
            profitEl.textContent = formatCurrency(profit);
            profitRatioEl.textContent = formatPercent(profitRatio);
            
            // 移除旧的颜色类
            profitEl.classList.remove('text-red', 'text-green');
            profitRatioEl.classList.remove('text-red', 'text-green');
            
            if (profit > 0) {
                profitEl.classList.add('text-red');
                profitRatioEl.classList.add('text-red');
            } else if (profit < 0) {
                profitEl.classList.add('text-green');
                profitRatioEl.classList.add('text-green');
            }
        } else {
            // 无持仓
            noHoldingEl.style.display = 'block';
            hasHoldingEl.style.display = 'none';
            sellBtn.style.display = 'none';
        }
        
    } catch (error) {
        console.error('加载基金详情失败:', error);
    }
}

// 初始化图表
function initChart() {
    chart = echarts.init(document.getElementById('chart'));
    
    window.addEventListener('resize', () => {
        chart?.resize();
    });
}

// 加载图表
async function loadChart(fundCode, period) {
    try {
        const data = await marketAPI.getChart(fundCode, period);
        
        if (!data.dates || data.dates.length === 0) {
            chart.clear();
            chart.setOption({
                title: {
                    text: '暂无数据',
                    left: 'center',
                    top: 'center',
                    textStyle: { color: '#999' }
                }
            });
            return;
        }
        
        const indicators = data.indicators || {};
        const trades = data.trades || { buy: [], sell: [] };
        
        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'cross' }
            },
            legend: {
                data: ['净值', 'MA5', 'MA10', 'MA20', '买入', '卖出'],
                bottom: 0,
                selected: {
                    '净值': true,
                    'MA5': false,
                    'MA10': false,
                    'MA20': false,
                    '买入': true,
                    '卖出': true
                }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: data.dates,
                boundaryGap: false
            },
            yAxis: {
                type: 'value',
                scale: true
            },
            series: [
                {
                    name: '净值',
                    type: 'line',
                    data: data.values,
                    smooth: true,
                    showSymbol: false,
                    lineStyle: { width: 2 },
                    itemStyle: { color: '#1890ff' },
                    areaStyle: {
                        color: {
                            type: 'linear',
                            x: 0, y: 0, x2: 0, y2: 1,
                            colorStops: [
                                { offset: 0, color: 'rgba(24,144,255,0.3)' },
                                { offset: 1, color: 'rgba(24,144,255,0.05)' }
                            ]
                        }
                    }
                },
                {
                    name: 'MA5',
                    type: 'line',
                    data: indicators.ma5,
                    smooth: true,
                    showSymbol: false,
                    lineStyle: { width: 1, type: 'dashed' },
                    itemStyle: { color: '#faad14' }
                },
                {
                    name: 'MA10',
                    type: 'line',
                    data: indicators.ma10,
                    smooth: true,
                    showSymbol: false,
                    lineStyle: { width: 1, type: 'dashed' },
                    itemStyle: { color: '#52c41a' }
                },
                {
                    name: 'MA20',
                    type: 'line',
                    data: indicators.ma20,
                    smooth: true,
                    showSymbol: false,
                    lineStyle: { width: 1, type: 'dashed' },
                    itemStyle: { color: '#722ed1' }
                },
                {
                    name: '买入',
                    type: 'scatter',
                    data: trades.buy,
                    symbol: 'circle',
                    symbolSize: 10,
                    itemStyle: {
                        color: '#ff6b6b',
                        borderColor: '#fff',
                        borderWidth: 2
                    },
                    z: 10
                },
                {
                    name: '卖出',
                    type: 'scatter',
                    data: trades.sell,
                    symbol: 'circle',
                    symbolSize: 10,
                    itemStyle: {
                        color: '#20c997',
                        borderColor: '#fff',
                        borderWidth: 2
                    },
                    z: 10
                }
            ]
        };
        
        chart.setOption(option, true);
        
        // 更新指标显示
        updateIndicators(indicators);
        
    } catch (error) {
        console.error('加载图表失败:', error);
    }
}

// 更新指标显示
function updateIndicators(indicators) {
    const getLastValue = (arr) => {
        if (!arr || arr.length === 0) return '-';
        for (let i = arr.length - 1; i >= 0; i--) {
            if (arr[i] !== null && arr[i] !== undefined) {
                return arr[i].toFixed(4);
            }
        }
        return '-';
    };
    
    document.getElementById('ai-ma5').textContent = getLastValue(indicators.ma5);
    document.getElementById('ai-ma10').textContent = getLastValue(indicators.ma10);
    document.getElementById('ai-ma20').textContent = getLastValue(indicators.ma20);
    document.getElementById('ai-rsi').textContent = getLastValue(indicators.rsi);
    document.getElementById('ai-macd').textContent = getLastValue(indicators.macd?.macd);
}

// 加载交易记录预览
async function loadTradePreview(fundCode) {
    try {
        const result = await tradeAPI.getAll(fundCode, 5);
        const trades = result.data || [];
        
        const card = document.getElementById('trade-preview-card');
        const container = document.getElementById('trade-preview');
        
        if (trades.length === 0) {
            card.style.display = 'none';
            return;
        }
        
        card.style.display = 'block';
        container.innerHTML = trades.map(trade => `
            <div class="trade-item">
                <span>${trade.trade_date}</span>
                <span class="type ${trade.trade_type}">${trade.trade_type === 'BUY' ? '买入' : '卖出'}</span>
                <span>${trade.confirm_net_value ? parseFloat(trade.confirm_net_value).toFixed(4) : '-'}</span>
                <span>${trade.confirm_shares ? parseFloat(trade.confirm_shares).toFixed(2) + '份' : '-'}</span>
                <span>¥${parseFloat(trade.amount).toFixed(2)}</span>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('加载交易记录失败:', error);
    }
}

// 搜索基金
let searchTimeout;
async function searchFunds(keyword) {
    clearTimeout(searchTimeout);
    
    if (!keyword || keyword.length < 2) {
        document.getElementById('search-results').classList.remove('show');
        return;
    }
    
    searchTimeout = setTimeout(async () => {
        try {
            const result = await fundAPI.search(keyword);
            const results = result.data || [];
            
            const container = document.getElementById('search-results');
            
            if (results.length === 0) {
                container.innerHTML = '<div class="search-result-item">未找到匹配的基金</div>';
            } else {
                container.innerHTML = results.map(fund => `
                    <div class="search-result-item" onclick="quickAddFund('${fund.fund_code}', '${fund.fund_name}')">
                        <div>${fund.fund_name}</div>
                        <div class="code">${fund.fund_code} ${fund.fund_type || ''}</div>
                    </div>
                `).join('');
            }
            
            container.classList.add('show');
            
        } catch (error) {
            console.error('搜索失败:', error);
        }
    }, 300);
}

// 快速添加基金
async function quickAddFund(code, name) {
    document.getElementById('search-input').value = '';
    document.getElementById('search-results').classList.remove('show');
    
    try {
        await fundAPI.add({ fund_code: code, fund_name: name });
        await loadFundList();
        selectFund(code);
    } catch (error) {
        alert('添加失败: ' + error.message);
    }
}

// 显示添加基金弹窗
function showAddFundModal() {
    document.getElementById('add-fund-code').value = '';
    document.getElementById('add-fund-name').value = '';
    showModal('add-fund-modal');
}

// 添加基金
async function addFund() {
    const code = document.getElementById('add-fund-code').value.trim();
    const name = document.getElementById('add-fund-name').value.trim();
    
    if (!code) {
        alert('请输入基金代码');
        return;
    }
    
    try {
        await fundAPI.add({ fund_code: code, fund_name: name || null });
        closeModal('add-fund-modal');
        await loadFundList();
        selectFund(code);
    } catch (error) {
        alert('添加失败: ' + error.message);
    }
}

// 显示交易弹窗
let tradeType = 'BUY';
function showTradeModal(type) {
    tradeType = type;
    document.getElementById('trade-modal-title').textContent = type === 'BUY' ? '买入' : '卖出';
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('trade-date').value = today;
    document.getElementById('confirm-date').value = today;
    document.getElementById('trade-amount').value = '';
    document.getElementById('confirm-net-value').value = '';
    document.getElementById('confirm-shares').value = '';
    showModal('trade-modal');
}

// 计算确认份额
function calculateConfirmShares() {
    const amount = parseFloat(document.getElementById('trade-amount').value);
    const netValue = parseFloat(document.getElementById('confirm-net-value').value);
    
    if (amount && netValue) {
        document.getElementById('confirm-shares').value = (amount / netValue).toFixed(2);
    }
}

// 提交交易
async function submitTrade() {
    const tradeDate = document.getElementById('trade-date').value;
    const confirmDate = document.getElementById('confirm-date').value;
    const amount = document.getElementById('trade-amount').value;
    const confirmNetValue = document.getElementById('confirm-net-value').value;
    const confirmShares = document.getElementById('confirm-shares').value;
    
    if (!tradeDate || !amount) {
        alert('请填写购买时间和金额');
        return;
    }
    
    try {
        await tradeAPI.add({
            fund_code: currentFundCode,
            trade_type: tradeType,
            trade_date: tradeDate,
            confirm_date: confirmDate || null,
            confirm_net_value: confirmNetValue || null,
            confirm_shares: confirmShares || null,
            amount: amount
        });
        
        closeModal('trade-modal');
        await loadFundDetail(currentFundCode);
        await loadHoldingsSummary();
        await loadTradePreview(currentFundCode);
        
    } catch (error) {
        alert('交易失败: ' + error.message);
    }
}

// 显示设置持仓弹窗
async function showSetHoldingModal() {
    try {
        const fund = await fundAPI.get(currentFundCode);
        
        // 填充当前持仓数据
        document.getElementById('set-shares').value = fund.total_shares ? parseFloat(fund.total_shares).toFixed(2) : '';
        document.getElementById('set-cost-price').value = fund.cost_price ? parseFloat(fund.cost_price).toFixed(4) : '';
        document.getElementById('set-total-cost').value = fund.total_cost ? parseFloat(fund.total_cost).toFixed(2) : '';
        
        showModal('set-holding-modal');
    } catch (error) {
        console.error('加载持仓信息失败:', error);
    }
}

// 计算总投入（份额 * 成本价）
function calculateTotalCost() {
    const shares = parseFloat(document.getElementById('set-shares').value);
    const costPrice = parseFloat(document.getElementById('set-cost-price').value);
    
    if (shares && costPrice) {
        document.getElementById('set-total-cost').value = (shares * costPrice).toFixed(2);
    }
}

// 保存持仓
async function saveHolding() {
    const shares = document.getElementById('set-shares').value;
    const costPrice = document.getElementById('set-cost-price').value;
    const totalCost = document.getElementById('set-total-cost').value;
    
    if (!shares || !costPrice || !totalCost) {
        alert('请填写完整信息');
        return;
    }
    
    try {
        await holdingAPI.update(currentFundCode, {
            total_shares: shares,
            cost_price: costPrice,
            total_cost: totalCost
        });
        
        closeModal('set-holding-modal');
        await loadFundDetail(currentFundCode);
        await loadHoldingsSummary();
        
    } catch (error) {
        alert('保存失败: ' + error.message);
    }
}

// 清空持仓
async function clearHolding() {
    if (!confirm('确定要清空该基金的持仓吗？')) return;
    
    try {
        await holdingAPI.update(currentFundCode, {
            total_shares: '0',
            cost_price: '0',
            total_cost: '0'
        });
        
        closeModal('set-holding-modal');
        await loadFundDetail(currentFundCode);
        await loadHoldingsSummary();
        
    } catch (error) {
        alert('清空失败: ' + error.message);
    }
}

// 显示交易历史
let allTrades = [];  // 存储所有交易记录用于编辑
async function showTradeHistory() {
    try {
        const result = await tradeAPI.getAll(currentFundCode, 100);
        allTrades = result.data || [];
        
        const tbody = document.getElementById('trade-history-body');
        tbody.innerHTML = allTrades.map(trade => `
            <tr>
                <td>${trade.trade_date}</td>
                <td>${trade.confirm_date || '-'}</td>
                <td class="type-${trade.trade_type}">${trade.trade_type === 'BUY' ? '买入' : '卖出'}</td>
                <td>${trade.confirm_net_value ? parseFloat(trade.confirm_net_value).toFixed(4) : '-'}</td>
                <td>${trade.confirm_shares ? parseFloat(trade.confirm_shares).toFixed(2) : '-'}</td>
                <td>¥${parseFloat(trade.amount).toFixed(2)}</td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="editTrade(${trade.id})">编辑</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteTrade(${trade.id})">删除</button>
                </td>
            </tr>
        `).join('');
        
        showModal('trade-history-modal');
        
    } catch (error) {
        console.error('加载交易历史失败:', error);
    }
}

// 编辑交易
let editingTradeId = null;
function editTrade(tradeId) {
    const trade = allTrades.find(t => t.id === tradeId);
    if (!trade) return;
    
    editingTradeId = tradeId;
    
    document.getElementById('edit-trade-type').value = trade.trade_type;
    document.getElementById('edit-trade-date').value = trade.trade_date;
    document.getElementById('edit-confirm-date').value = trade.confirm_date || '';
    document.getElementById('edit-trade-amount').value = trade.amount;
    document.getElementById('edit-confirm-net-value').value = trade.confirm_net_value || '';
    document.getElementById('edit-confirm-shares').value = trade.confirm_shares || '';
    
    showModal('edit-trade-modal');
}

// 保存编辑的交易
async function saveEditTrade() {
    if (!editingTradeId) return;
    
    const tradeType = document.getElementById('edit-trade-type').value;
    const tradeDate = document.getElementById('edit-trade-date').value;
    const confirmDate = document.getElementById('edit-confirm-date').value;
    const amount = document.getElementById('edit-trade-amount').value;
    const confirmNetValue = document.getElementById('edit-confirm-net-value').value;
    const confirmShares = document.getElementById('edit-confirm-shares').value;
    
    if (!tradeDate || !amount) {
        alert('请填写购买时间和金额');
        return;
    }
    
    try {
        await tradeAPI.update(editingTradeId, {
            trade_type: tradeType,
            trade_date: tradeDate,
            confirm_date: confirmDate || null,
            confirm_net_value: confirmNetValue || null,
            confirm_shares: confirmShares || null,
            amount: amount
        });
        
        // 重新计算持仓
        await tradeAPI.recalculate(currentFundCode);
        
        closeModal('edit-trade-modal');
        await showTradeHistory();
        await loadFundDetail(currentFundCode);
        await loadHoldingsSummary();
        await loadTradePreview(currentFundCode);
        
    } catch (error) {
        alert('保存失败: ' + error.message);
    }
}

// 删除交易
async function deleteTrade(tradeId) {
    if (!confirm('确定删除该交易记录？')) return;
    
    try {
        await tradeAPI.delete(tradeId);
        await tradeAPI.recalculate(currentFundCode);
        
        await showTradeHistory();
        await loadFundDetail(currentFundCode);
        await loadHoldingsSummary();
        await loadTradePreview(currentFundCode);
        
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

// 获取 AI 建议
async function getAISuggestion() {
    const resultEl = document.getElementById('ai-result');
    resultEl.innerHTML = '<div class="loading"></div> 分析中...';
    
    try {
        const result = await aiAPI.suggest(currentFundCode);
        
        if (result.error) {
            resultEl.innerHTML = `<p style="color: #ff4d4f;">${result.error}</p>`;
            return;
        }
        
        // 使用 marked.js 渲染 Markdown
        if (typeof marked !== 'undefined') {
            resultEl.innerHTML = `<div class="markdown-body">${marked.parse(result.analysis)}</div>`;
        } else {
            // 如果 marked 不可用，简单格式化
            resultEl.innerHTML = formatMarkdownSimple(result.analysis);
        }
        
        // 更新指标
        if (result.indicators) {
            if (result.indicators.ma5) document.getElementById('ai-ma5').textContent = result.indicators.ma5;
            if (result.indicators.ma10) document.getElementById('ai-ma10').textContent = result.indicators.ma10;
            if (result.indicators.ma20) document.getElementById('ai-ma20').textContent = result.indicators.ma20;
            if (result.indicators.rsi) document.getElementById('ai-rsi').textContent = result.indicators.rsi;
            if (result.indicators.macd) document.getElementById('ai-macd').textContent = result.indicators.macd;
        }
        
    } catch (error) {
        resultEl.innerHTML = `<p style="color: #ff4d4f;">分析失败: ${error.message}</p>`;
    }
}

// 简单的 Markdown 格式化（备用）
function formatMarkdownSimple(text) {
    if (!text) return '';
    
    return text
        // 标题
        .replace(/^### (.*$)/gm, '<h4>$1</h4>')
        .replace(/^## (.*$)/gm, '<h3>$1</h3>')
        .replace(/^# (.*$)/gm, '<h2>$1</h2>')
        // 粗体
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // 斜体
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // 列表
        .replace(/^- (.*$)/gm, '<li>$1</li>')
        .replace(/^(\d+)\. (.*$)/gm, '<li>$2</li>')
        // 换行
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
}

// 删除基金
async function deleteFund() {
    if (!currentFundCode) return;
    
    if (!confirm('确定要删除该基金吗？这将同时删除相关的持仓和交易记录。')) {
        return;
    }
    
    try {
        await fundAPI.delete(currentFundCode);
        
        currentFundCode = null;
        document.getElementById('no-selection').style.display = 'flex';
        document.getElementById('fund-detail').style.display = 'none';
        
        await loadFundList();
        await loadHoldingsSummary();
        
        alert('基金已删除');
        
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

// 显示设置弹窗
async function showSettingsModal() {
    try {
        const settings = await aiAPI.getSettings();
        
        document.getElementById('setting-api-key').value = settings.deepseek_api_key || '';
        document.getElementById('setting-base-url').value = settings.deepseek_base_url || '';
        document.getElementById('setting-model').value = settings.deepseek_model || 'deepseek-chat';
        
        showModal('settings-modal');
        
    } catch (error) {
        console.error('加载设置失败:', error);
    }
}

// 保存设置
async function saveSettings() {
    const apiKey = document.getElementById('setting-api-key').value.trim();
    const baseUrl = document.getElementById('setting-base-url').value.trim();
    const model = document.getElementById('setting-model').value;
    
    try {
        await aiAPI.updateSettings({
            deepseek_api_key: apiKey || null,
            deepseek_base_url: baseUrl || null,
            deepseek_model: model
        });
        
        closeModal('settings-modal');
        alert('设置已保存');
        
    } catch (error) {
        alert('保存失败: ' + error.message);
    }
}

// 刷新所有数据
async function refreshAll() {
    try {
        await marketAPI.syncAll();
        await loadFundList();
        await loadHoldingsSummary();
        
        if (currentFundCode) {
            await loadFundDetail(currentFundCode);
            await loadChart(currentFundCode, currentPeriod);
            await loadTradePreview(currentFundCode);
        }
        
        document.getElementById('last-update').textContent = '最后更新: ' + new Date().toLocaleString();
        
    } catch (error) {
        alert('刷新失败: ' + error.message);
    }
}

// 工具函数
function formatCurrency(value) {
    if (value === null || value === undefined) return '¥0.00';
    const num = parseFloat(value);
    const sign = num >= 0 ? '' : '-';
    return sign + '¥' + Math.abs(num).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatPercent(value) {
    if (value === null || value === undefined) return '0.00%';
    const num = parseFloat(value);
    const sign = num > 0 ? '+' : '';
    return sign + num.toFixed(2) + '%';
}

// 弹窗控制
function showModal(id) {
    document.getElementById(id).classList.add('show');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('show');
}

// 点击弹窗外部关闭
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    });
});

// 隐藏搜索结果
document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-box')) {
        document.getElementById('search-results').classList.remove('show');
    }
});
