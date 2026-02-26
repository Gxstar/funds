/** 主应用程序 */

let currentFundCode = null;
let chart = null;
let homePieChart = null;
let currentPeriod = '1y';
let currentView = 'home'; // 'home' or 'detail'

// AI 分析结果缓存 { fundCode: { analysis, indicators, timestamp } }
const aiAnalysisCache = {};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    initChart();
    initHomePieChart();
    bindEvents();
});

function initApp() {
    loadFundList();
    loadHoldingsSummary();
    loadHomePage();
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

// 初始化首页饼图
function initHomePieChart() {
    homePieChart = echarts.init(document.getElementById('home-pie-chart'));
    
    window.addEventListener('resize', () => {
        homePieChart?.resize();
    });
}

// 显示首页
function showHomePage() {
    currentView = 'home';
    currentFundCode = null;
    
    document.getElementById('home-page').style.display = 'block';
    document.getElementById('no-selection').style.display = 'none';
    document.getElementById('fund-detail').style.display = 'none';
    
    // 更新基金列表选中状态
    document.querySelectorAll('.fund-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 刷新首页数据
    loadHomePage();
    
    // 饼图 resize
    setTimeout(() => {
        if (homePieChart) {
            homePieChart.resize();
        }
    }, 100);
}

// 显示基金详情
function showFundDetail() {
    currentView = 'detail';
    
    document.getElementById('home-page').style.display = 'none';
    document.getElementById('no-selection').style.display = 'none';
    document.getElementById('fund-detail').style.display = 'block';
    
    // 确保 ECharts 正确渲染
    setTimeout(() => {
        if (chart) {
            chart.resize();
        }
    }, 100);
}

// 加载首页数据
async function loadHomePage() {
    if (currentView !== 'home') return;
    
    await Promise.all([
        loadHomeSummary(),
        loadHomePieChart(),
        loadHomeTodayChange(),
        loadHomeRecentTrades(),
        loadHomeHoldings()
    ]);
}

// 加载首页汇总数据
async function loadHomeSummary() {
    try {
        const [summary, settings] = await Promise.all([
            holdingAPI.getSummary(),
            aiAPI.getSettings()
        ]);
        
        document.getElementById('home-total-cost').textContent = formatCurrency(summary.total_cost);
        document.getElementById('home-total-market').textContent = formatCurrency(summary.total_market_value);
        
        const profitEl = document.getElementById('home-total-profit');
        const profitRateEl = document.getElementById('home-profit-rate');
        
        profitEl.textContent = formatCurrency(summary.total_profit);
        profitRateEl.textContent = formatPercent(summary.profit_rate);
        
        profitEl.classList.remove('text-red', 'text-green');
        profitRateEl.classList.remove('text-red', 'text-green');
        
        if (summary.total_profit > 0) {
            profitEl.classList.add('text-red');
            profitRateEl.classList.add('text-red');
        } else if (summary.total_profit < 0) {
            profitEl.classList.add('text-green');
            profitRateEl.classList.add('text-green');
        }
        
        // 计算仓位比例
        const positionRatioEl = document.getElementById('home-position-ratio');
        const positionDetailEl = document.getElementById('home-position-detail');
        
        const totalPosition = parseFloat(settings.total_position_amount) || 0;
        if (totalPosition > 0) {
            const ratio = (summary.total_market_value / totalPosition * 100);
            const available = totalPosition - summary.total_market_value;
            
            positionRatioEl.textContent = ratio.toFixed(1) + '%';
            positionDetailEl.textContent = `剩余 ${formatCurrency(available)}`;
            
            // 根据仓位高低显示不同颜色
            positionRatioEl.classList.remove('text-red', 'text-green');
            if (ratio >= 90) {
                positionRatioEl.classList.add('text-red'); // 高仓位
            } else if (ratio <= 30) {
                positionRatioEl.classList.add('text-green'); // 低仓位
            }
        } else {
            positionRatioEl.textContent = '-';
            positionDetailEl.textContent = '未设置满仓金额';
            positionRatioEl.classList.remove('text-red', 'text-green');
        }
        
    } catch (error) {
        console.error('加载首页汇总失败:', error);
    }
}

// 加载持仓分布饼图
async function loadHomePieChart() {
    try {
        const funds = await fundAPI.getAll();
        const holdings = (funds.data || []).filter(f => f.total_shares && parseFloat(f.total_shares) > 0);
        
        if (holdings.length === 0) {
            homePieChart.setOption({
                title: {
                    text: '暂无持仓',
                    left: 'center',
                    top: 'center',
                    textStyle: { color: '#999' }
                }
            });
            return;
        }
        
        const data = holdings.map(f => {
            const shares = parseFloat(f.total_shares) || 0;
            const netValue = parseFloat(f.last_net_value) || 0;
            return {
                name: f.fund_name || f.fund_code,
                value: Math.round(shares * netValue)
            };
        });
        
        const option = {
            tooltip: {
                trigger: 'item',
                formatter: '{b}: ¥{c} ({d}%)'
            },
            legend: {
                orient: 'vertical',
                right: 10,
                top: 'center',
                itemWidth: 10,
                itemHeight: 10,
                textStyle: { fontSize: 12 }
            },
            series: [{
                type: 'pie',
                radius: ['40%', '70%'],
                center: ['35%', '50%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 6,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: false
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 14,
                        fontWeight: 'bold'
                    }
                },
                data: data
            }]
        };
        
        homePieChart.setOption(option, true);
        
    } catch (error) {
        console.error('加载饼图失败:', error);
    }
}

// 加载今日涨跌
async function loadHomeTodayChange() {
    try {
        const funds = await fundAPI.getAll();
        const holdings = (funds.data || []).filter(f => f.total_shares && parseFloat(f.total_shares) > 0);
        
        const container = document.getElementById('home-today-change');
        
        if (holdings.length === 0) {
            container.innerHTML = '<div class="no-data">暂无持仓</div>';
            return;
        }
        
        // 按涨跌幅排序
        holdings.sort((a, b) => (b.last_growth_rate || 0) - (a.last_growth_rate || 0));
        
        container.innerHTML = holdings.map(fund => {
            const growthRate = fund.last_growth_rate;
            const growthClass = growthRate > 0 ? 'positive' : growthRate < 0 ? 'negative' : '';
            const growthText = growthRate ? `${growthRate > 0 ? '+' : ''}${growthRate.toFixed(2)}%` : '-';
            const dateStr = fund.last_price_date ? `<span class="date">${fund.last_price_date}</span>` : '';
            
            return `
                <div class="today-change-item" onclick="selectFundFromHome('${fund.fund_code}')">
                    <div>
                        <span class="name">${fund.fund_name || '-'}</span>
                        <span class="code">${fund.fund_code}</span>
                    </div>
                    <div class="change-wrapper">
                        ${dateStr}
                        <span class="change ${growthClass}">${growthText}</span>
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('加载今日涨跌失败:', error);
    }
}

// 加载近期交易
async function loadHomeRecentTrades() {
    try {
        const result = await tradeAPI.getAll(null, 5);
        const trades = result.data || [];
        
        const container = document.getElementById('home-recent-trades');
        
        if (trades.length === 0) {
            container.innerHTML = '<div class="no-data">暂无交易记录</div>';
            return;
        }
        
        container.innerHTML = trades.map(trade => {
            const isBuy = trade.trade_type === 'BUY';
            const typeText = isBuy ? '买入' : '卖出';
            const typeClass = isBuy ? 'buy' : 'sell';
            
            return `
                <div class="home-trade-item" onclick="selectFundFromHome('${trade.fund_code}')">
                    <div class="info">
                        <span class="fund-name">${trade.fund_name || trade.fund_code}</span>
                        <span class="trade-info">${trade.trade_date} · ${typeText}</span>
                    </div>
                    <span class="amount ${typeClass}">${isBuy ? '-' : '+'}¥${parseFloat(trade.amount).toFixed(2)}</span>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('加载近期交易失败:', error);
    }
}

// 加载持仓基金列表
async function loadHomeHoldings() {
    try {
        const funds = await fundAPI.getAll();
        const holdings = (funds.data || []).filter(f => f.total_shares && parseFloat(f.total_shares) > 0);
        
        const container = document.getElementById('home-holding-list');
        
        if (holdings.length === 0) {
            container.innerHTML = '<div class="no-data">暂无持仓</div>';
            return;
        }
        
        // 按市值排序
        holdings.sort((a, b) => {
            const valueA = parseFloat(a.total_shares) * parseFloat(a.last_net_value || 0);
            const valueB = parseFloat(b.total_shares) * parseFloat(b.last_net_value || 0);
            return valueB - valueA;
        });
        
        container.innerHTML = holdings.map(fund => {
            const shares = parseFloat(fund.total_shares) || 0;
            const netValue = parseFloat(fund.last_net_value) || 0;
            const totalCost = parseFloat(fund.total_cost) || 0;
            const marketValue = shares * netValue;
            const profit = marketValue - totalCost;
            const profitRate = totalCost ? (profit / totalCost * 100) : 0;
            
            const profitClass = profit > 0 ? 'positive' : profit < 0 ? 'negative' : '';
            
            return `
                <div class="home-holding-item" onclick="selectFundFromHome('${fund.fund_code}')">
                    <div class="info">
                        <span class="name">${fund.fund_name || '-'}</span>
                        <span class="code">${fund.fund_code}</span>
                    </div>
                    <div class="holding-info">
                        <span class="market-value">${formatCurrency(marketValue)}</span>
                        <span class="profit ${profitClass}">${formatCurrency(profit)} (${formatPercent(profitRate)})</span>
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('加载持仓列表失败:', error);
    }
}

// 从首页选择基金
async function selectFundFromHome(fundCode) {
    currentFundCode = fundCode;
    
    // 更新列表选中状态
    document.querySelectorAll('.fund-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('onclick')?.includes(fundCode)) {
            item.classList.add('active');
        }
    });
    
    showFundDetail();
    
    await loadFundDetail(fundCode);
    await loadChart(fundCode, currentPeriod);
    await loadTradePreview(fundCode);
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
            const dateStr = fund.last_price_date || '';
            
            return `
                <div class="fund-item ${fund.fund_code === currentFundCode ? 'active' : ''}" 
                     onclick="selectFund('${fund.fund_code}')">
                    <div class="name">${fund.fund_name || '-'}</div>
                    <div class="info">
                        <span class="code">${fund.fund_code}</span>
                        <span class="growth ${growthClass}">${growthText}</span>
                        ${dateStr ? `<span class="growth-date">${dateStr}</span>` : ''}
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
    
    showFundDetail();
    
    // 加载基金详情
    await loadFundDetail(fundCode);
    await loadChart(fundCode, currentPeriod);
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
            const dateStr = fund.last_price_date ? ` (${fund.last_price_date})` : '';
            growthEl.textContent = formatPercent(fund.last_growth_rate) + dateStr;
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
        
        // 更新 AI 分析结果显示（根据缓存）
        updateAIDisplay(fundCode);
        
    } catch (error) {
        console.error('加载基金详情失败:', error);
    }
}

// 更新 AI 分析结果显示
function updateAIDisplay(fundCode) {
    const resultEl = document.getElementById('ai-result');
    const cache = aiAnalysisCache[fundCode];
    
    if (cache) {
        // 显示缓存的分析结果
        const timeStr = cache.timestamp ? formatDateTime(cache.timestamp) : '';
        let html = '';
        
        if (timeStr) {
            html += `<div class="ai-analysis-time">分析时间: ${timeStr}</div>`;
        }
        
        if (typeof marked !== 'undefined') {
            html += `<div class="markdown-body">${marked.parse(cache.analysis)}</div>`;
        } else {
            html += formatMarkdownSimple(cache.analysis);
        }
        
        resultEl.innerHTML = html;
        
        // 更新指标
        if (cache.indicators) {
            if (cache.indicators.ma5) document.getElementById('ai-ma5').textContent = cache.indicators.ma5;
            if (cache.indicators.ma10) document.getElementById('ai-ma10').textContent = cache.indicators.ma10;
            if (cache.indicators.ma20) document.getElementById('ai-ma20').textContent = cache.indicators.ma20;
            if (cache.indicators.rsi) document.getElementById('ai-rsi').textContent = cache.indicators.rsi;
            if (cache.indicators.macd) document.getElementById('ai-macd').textContent = cache.indicators.macd;
        }
    } else {
        // 没有缓存，显示默认提示
        resultEl.innerHTML = '<p class="placeholder">点击"分析"按钮获取 AI 建议</p>';
    }
}

// 格式化日期时间
function formatDateTime(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
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
    const fundCode = currentFundCode;
    const resultEl = document.getElementById('ai-result');
    
    // 显示加载状态和分析开始时间
    const startTime = new Date();
    const startTimeStr = formatDateTime(startTime.toISOString());
    resultEl.innerHTML = `<div class="ai-analysis-time">分析开始: ${startTimeStr}</div><div class="loading"></div> 分析中...`;
    
    try {
        const result = await aiAPI.suggest(fundCode);
        
        // 检查是否还在当前基金页面
        if (currentFundCode !== fundCode) {
            return; // 已切换到其他基金，不更新显示
        }
        
        if (result.error) {
            resultEl.innerHTML = `<p style="color: #ff4d4f;">${result.error}</p>`;
            return;
        }
        
        // 缓存分析结果
        aiAnalysisCache[fundCode] = {
            analysis: result.analysis,
            indicators: result.indicators,
            timestamp: result.timestamp || new Date().toISOString()
        };
        
        // 显示分析结果和时间
        const timeStr = formatDateTime(aiAnalysisCache[fundCode].timestamp);
        let html = `<div class="ai-analysis-time">分析时间: ${timeStr}</div>`;
        
        // 使用 marked.js 渲染 Markdown
        if (typeof marked !== 'undefined') {
            html += `<div class="markdown-body">${marked.parse(result.analysis)}</div>`;
        } else {
            html += formatMarkdownSimple(result.analysis);
        }
        
        resultEl.innerHTML = html;
        
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

// AI 持仓组合分析
async function analyzePortfolio() {
    const summaryEl = document.getElementById('portfolio-summary');
    const contentEl = document.getElementById('portfolio-analysis-content');
    
    // 显示模态框和加载状态
    showModal('portfolio-analysis-modal');
    summaryEl.innerHTML = '';
    contentEl.innerHTML = '<div class="loading-wrapper"><div class="loading"></div><span>正在分析您的持仓组合，请稍候...</span></div>';
    
    try {
        const result = await aiAPI.analyze();
        
        if (result.error) {
            contentEl.innerHTML = `<p style="color: #ff4d4f; text-align: center; padding: 20px;">${result.error}</p>`;
            return;
        }
        
        // 显示汇总信息
        if (result.summary) {
            const summary = result.summary;
            summaryEl.innerHTML = `
                <div class="summary-row">
                    <div class="summary-item">
                        <span class="label">持有基金</span>
                        <span class="value">${summary.fund_count} 只</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">总投入</span>
                        <span class="value">${formatCurrency(summary.total_cost)}</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">总市值</span>
                        <span class="value">${formatCurrency(summary.total_market_value)}</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">总盈亏</span>
                        <span class="value ${summary.total_profit > 0 ? 'text-red' : summary.total_profit < 0 ? 'text-green' : ''}">${formatCurrency(summary.total_profit)} (${formatPercent(summary.profit_rate)})</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">账户仓位</span>
                        <span class="value">${summary.position_ratio.toFixed(1)}%</span>
                    </div>
                </div>
            `;
        }
        
        // 显示分析结果
        if (result.analysis) {
            const analysisHtml = typeof marked !== 'undefined' 
                ? marked.parse(result.analysis) 
                : formatMarkdownSimple(result.analysis);
            
            contentEl.innerHTML = `<div class="markdown-body">${analysisHtml}</div>`;
        }
        
    } catch (error) {
        contentEl.innerHTML = `<p style="color: #ff4d4f; text-align: center; padding: 20px;">分析失败: ${error.message}</p>`;
    }
}

// 关闭持仓分析（保留兼容性）
function closePortfolioAnalysis() {
    closeModal('portfolio-analysis-modal');
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
        
        // API Key: 如果已配置则显示占位符，不显示真实值
        const apiKeyInput = document.getElementById('setting-api-key');
        if (settings.api_key_configured) {
            apiKeyInput.value = '';
            apiKeyInput.placeholder = '已配置（留空保持不变）';
        } else {
            apiKeyInput.value = '';
            apiKeyInput.placeholder = 'sk-...';
        }
        
        document.getElementById('setting-base-url').value = settings.deepseek_base_url || '';
        document.getElementById('setting-model').value = settings.deepseek_model || 'deepseek-chat';
        document.getElementById('setting-total-position').value = settings.total_position_amount && settings.total_position_amount !== '0' ? settings.total_position_amount : '';
        
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
    const totalPosition = document.getElementById('setting-total-position').value.trim();
    
    try {
        // 保存 AI 设置（只发送有值的字段）
        const aiSettings = {};
        if (apiKey) aiSettings.deepseek_api_key = apiKey;
        if (baseUrl) aiSettings.deepseek_base_url = baseUrl;
        if (model) aiSettings.deepseek_model = model;
        
        if (Object.keys(aiSettings).length > 0) {
            await aiAPI.updateSettings(aiSettings);
        }
        
        // 保存仓位设置
        await aiAPI.updatePositionSetting({
            total_position_amount: totalPosition || ''
        });
        
        closeModal('settings-modal');
        showToast('设置已保存', 'success');
        
        // 刷新首页数据
        if (currentView === 'home') {
            loadHomeSummary();
        }
        
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
}

// 刷新所有数据
async function refreshAll() {
    const btn = document.querySelector('[onclick="refreshAll()"]');
    const originalText = btn?.innerHTML;
    if (btn) {
        btn.innerHTML = '⟳ 刷新中...';
        btn.disabled = true;
    }
    
    try {
        const result = await marketAPI.syncAll();
        await loadFundList();
        await loadHoldingsSummary();
        
        if (currentFundCode) {
            await loadFundDetail(currentFundCode);
            await loadChart(currentFundCode, currentPeriod);
            await loadTradePreview(currentFundCode);
        }
        
        document.getElementById('last-update').textContent = '最后更新: ' + new Date().toLocaleString();
        
        // 显示成功提示
        showToast('数据刷新成功', 'success');
        
    } catch (error) {
        showToast('刷新失败: ' + error.message, 'error');
    } finally {
        if (btn) {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
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

// 显示提示信息
function showToast(message, type = 'info') {
    // 移除已存在的 toast
    const existingToast = document.querySelector('.toast-message');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = `toast-message toast-${type}`;
    toast.innerHTML = message;
    document.body.appendChild(toast);
    
    // 显示动画
    setTimeout(() => toast.classList.add('show'), 10);
    
    // 自动消失
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
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
