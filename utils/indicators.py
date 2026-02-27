"""技术指标计算"""
from decimal import Decimal
from typing import Optional
import math


def calculate_ma(prices: list[Decimal], period: int) -> list[Optional[Decimal]]:
    """计算移动平均线 MA
    
    Args:
        prices: 价格列表（按时间顺序）
        period: 周期（如 5, 10, 20）
    
    Returns:
        MA 值列表，前 period-1 个为 None
    """
    result = [None] * (period - 1)
    for i in range(period - 1, len(prices)):
        ma = sum(prices[i - period + 1:i + 1]) / period
        result.append(ma)
    return result


def calculate_ema(prices: list[Decimal], period: int) -> list[Decimal]:
    """计算指数移动平均线 EMA
    
    EMA = 当日价格 * k + 昨日EMA * (1 - k)
    k = 2 / (period + 1)
    """
    if not prices:
        return []
    
    k = Decimal("2") / (period + 1)
    result = [prices[0]]  # 第一个 EMA 等于第一个价格
    
    for i in range(1, len(prices)):
        ema = prices[i] * k + result[-1] * (1 - k)
        result.append(ema)
    
    return result


def calculate_macd(
    prices: list[Decimal],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> dict:
    """计算 MACD 指标
    
    Args:
        prices: 价格列表
        fast_period: 快线周期，默认 12
        slow_period: 慢线周期，默认 26
        signal_period: 信号线周期，默认 9
    
    Returns:
        {
            "dif": DIF 值列表,
            "dea": DEA（信号线）值列表,
            "macd": MACD 柱值列表
        }
    """
    if len(prices) < slow_period:
        return {"dif": [], "dea": [], "macd": []}
    
    # 计算 EMA
    ema_fast = calculate_ema(prices, fast_period)
    ema_slow = calculate_ema(prices, slow_period)
    
    # 计算 DIF
    dif = [ema_fast[i] - ema_slow[i] for i in range(len(prices))]
    
    # 计算 DEA（DIF 的 EMA）
    dea = calculate_ema(dif, signal_period)
    
    # 计算 MACD 柱
    macd = [(dif[i] - dea[i]) * 2 for i in range(len(prices))]
    
    return {
        "dif": dif,
        "dea": dea,
        "macd": macd
    }


def calculate_rsi(prices: list[Decimal], period: int = 14) -> list[Optional[Decimal]]:
    """计算相对强弱指标 RSI
    
    RSI = 100 - 100 / (1 + RS)
    RS = 平均上涨幅度 / 平均下跌幅度
    
    Args:
        prices: 价格列表
        period: 周期，默认 14
    
    Returns:
        RSI 值列表，前 period 个为 None
    """
    if len(prices) < period + 1:
        return [None] * len(prices)
    
    # 计算价格变化
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    
    # 初始平均上涨和下跌
    gains = [max(c, Decimal("0")) for c in changes[:period]]
    losses = [abs(min(c, Decimal("0"))) for c in changes[:period]]
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    result = [None] * period
    
    # 第一个 RSI
    if avg_loss == 0:
        result.append(Decimal("100"))
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - 100 / (1 + rs)
        result.append(rsi)
    
    # 后续 RSI（使用平滑方法）
    for i in range(period, len(changes)):
        gain = max(changes[i], Decimal("0"))
        loss = abs(min(changes[i], Decimal("0")))
        
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        
        if avg_loss == 0:
            result.append(Decimal("100"))
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - 100 / (1 + rs)
            result.append(rsi)
    
    return result


def calculate_kdj(
    high_prices: list[Decimal],
    low_prices: list[Decimal],
    close_prices: list[Decimal],
    n: int = 9,
    m1: int = 3,
    m2: int = 3
) -> dict:
    """计算 KDJ 指标
    
    RSV = (收盘价 - N日最低价) / (N日最高价 - N日最低价) * 100
    K = RSV 的 M1 日移动平均
    D = K 的 M2 日移动平均
    J = 3 * K - 2 * D
    
    注意：场外基金没有高低价，使用收盘价模拟
    """
    length = len(close_prices)
    if length < n:
        return {"k": [], "d": [], "j": []}
    
    # 对于基金，用收盘价代替高低价
    rsv_list = []
    
    for i in range(n - 1, length):
        period_high = max(close_prices[i - n + 1:i + 1])
        period_low = min(close_prices[i - n + 1:i + 1])
        
        if period_high == period_low:
            rsv = Decimal("50")
        else:
            rsv = (close_prices[i] - period_low) / (period_high - period_low) * 100
        
        rsv_list.append(rsv)
    
    # 计算 K 值
    k_list = []
    k = Decimal("50")  # 初始 K 值
    for rsv in rsv_list:
        k = (k * (m1 - 1) + rsv) / m1
        k_list.append(k)
    
    # 计算 D 值
    d_list = []
    d = Decimal("50")  # 初始 D 值
    for k in k_list:
        d = (d * (m2 - 1) + k) / m2
        d_list.append(d)
    
    # 计算 J 值
    j_list = [3 * k_list[i] - 2 * d_list[i] for i in range(len(k_list))]
    
    # 补齐前面的 None
    k_result = [None] * (n - 1) + k_list
    d_result = [None] * (n - 1) + d_list
    j_result = [None] * (n - 1) + j_list
    
    return {
        "k": k_result,
        "d": d_result,
        "j": j_result
    }


def calculate_boll(
    prices: list[Decimal],
    period: int = 20,
    std_dev: int = 2
) -> dict:
    """计算布林带
    
    中轨 = N 日移动平均
    上轨 = 中轨 + K * N 日标准差
    下轨 = 中轨 - K * N 日标准差
    
    Args:
        prices: 价格列表
        period: 周期，默认 20
        std_dev: 标准差倍数，默认 2
    
    Returns:
        {
            "upper": 上轨列表,
            "middle": 中轨列表,
            "lower": 下轨列表
        }
    """
    if len(prices) < period:
        return {
            "upper": [None] * len(prices),
            "middle": [None] * len(prices),
            "lower": [None] * len(prices)
        }
    
    middle = calculate_ma(prices, period)
    upper = []
    lower = []
    
    for i in range(len(prices)):
        if middle[i] is None:
            upper.append(None)
            lower.append(None)
            continue
        
        # 计算标准差
        period_prices = prices[i - period + 1:i + 1]
        avg = middle[i]
        variance = sum((p - avg) ** 2 for p in period_prices) / period
        std = Decimal(str(math.sqrt(float(variance))))
        
        upper.append(avg + std * std_dev)
        lower.append(avg - std * std_dev)
    
    return {
        "upper": upper,
        "middle": middle,
        "lower": lower
    }


def calculate_max_drawdown(prices: list[Decimal]) -> dict:
    """计算最大回撤
    
    最大回撤 = (峰值 - 谷值) / 峰值
    
    Args:
        prices: 价格列表（按时间顺序）
    
    Returns:
        {
            "max_drawdown": 最大回撤比例,
            "max_drawdown_pct": 最大回撤百分比,
            "peak_date_index": 峰值位置索引,
            "trough_date_index": 谷值位置索引
        }
    """
    if len(prices) < 2:
        return {
            "max_drawdown": Decimal("0"),
            "max_drawdown_pct": Decimal("0"),
            "peak_date_index": 0,
            "trough_date_index": 0
        }
    
    max_drawdown = Decimal("0")
    peak = prices[0]
    peak_idx = 0
    trough_idx = 0
    max_peak_idx = 0
    
    for i in range(1, len(prices)):
        if prices[i] > peak:
            peak = prices[i]
            peak_idx = i
        else:
            drawdown = (peak - prices[i]) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                trough_idx = i
                max_peak_idx = peak_idx
    
    return {
        "max_drawdown": max_drawdown,
        "max_drawdown_pct": max_drawdown * 100,
        "peak_date_index": max_peak_idx,
        "trough_date_index": trough_idx
    }


def calculate_volatility(prices: list[Decimal], annualize: bool = True) -> dict:
    """计算波动率（标准差）
    
    Args:
        prices: 价格列表
        annualize: 是否年化（假设一年约 252 个交易日）
    
    Returns:
        {
            "daily_volatility": 日波动率,
            "daily_volatility_pct": 日波动率百分比,
            "annualized_volatility": 年化波动率（如果 annualize=True）,
            "annualized_volatility_pct": 年化波动率百分比
        }
    """
    if len(prices) < 2:
        return {
            "daily_volatility": Decimal("0"),
            "daily_volatility_pct": Decimal("0"),
            "annualized_volatility": None,
            "annualized_volatility_pct": None
        }
    
    # 计算日收益率
    returns = []
    for i in range(1, len(prices)):
        if prices[i - 1] != 0:
            ret = (prices[i] - prices[i - 1]) / prices[i - 1]
            returns.append(ret)
    
    if not returns:
        return {
            "daily_volatility": Decimal("0"),
            "daily_volatility_pct": Decimal("0"),
            "annualized_volatility": None,
            "annualized_volatility_pct": None
        }
    
    # 计算标准差
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    daily_vol = Decimal(str(math.sqrt(float(variance))))
    
    result = {
        "daily_volatility": daily_vol,
        "daily_volatility_pct": daily_vol * 100,
        "annualized_volatility": None,
        "annualized_volatility_pct": None
    }
    
    if annualize:
        # 年化波动率 = 日波动率 * sqrt(252)
        annualized = daily_vol * Decimal(str(math.sqrt(252)))
        result["annualized_volatility"] = annualized
        result["annualized_volatility_pct"] = annualized * 100
    
    return result


def calculate_sharpe_ratio(
    prices: list[Decimal],
    risk_free_rate: Decimal = Decimal("0.015")  # 默认年化无风险利率 1.5%
) -> dict:
    """计算夏普比率
    
    夏普比率 = (年化收益率 - 无风险利率) / 年化波动率
    
    Args:
        prices: 价格列表
        risk_free_rate: 年化无风险利率（默认 1.5%）
    
    Returns:
        {
            "total_return": 总收益率,
            "annualized_return": 年化收益率,
            "sharpe_ratio": 夏普比率
        }
    """
    if len(prices) < 2:
        return {
            "total_return": Decimal("0"),
            "annualized_return": Decimal("0"),
            "sharpe_ratio": None
        }
    
    # 总收益率
    total_return = (prices[-1] - prices[0]) / prices[0]
    
    # 年化收益率（假设数据为日频，计算实际天数）
    days = len(prices) - 1
    if days > 0:
        annualized_return = ((1 + total_return) ** (252 / days)) - 1
    else:
        annualized_return = Decimal("0")
    
    # 获取年化波动率
    vol_data = calculate_volatility(prices, annualize=True)
    annualized_vol = vol_data.get("annualized_volatility")
    
    # 计算夏普比率
    sharpe = None
    if annualized_vol and annualized_vol > 0:
        sharpe = (annualized_return - risk_free_rate) / annualized_vol
    
    return {
        "total_return": total_return,
        "total_return_pct": total_return * 100,
        "annualized_return": annualized_return,
        "annualized_return_pct": annualized_return * 100,
        "sharpe_ratio": sharpe
    }


def calculate_risk_metrics(prices: list[Decimal]) -> dict:
    """计算综合风险指标
    
    Args:
        prices: 价格列表
    
    Returns:
        包含最大回撤、波动率、夏普比率等指标的字典
    """
    drawdown = calculate_max_drawdown(prices)
    volatility = calculate_volatility(prices)
    sharpe = calculate_sharpe_ratio(prices)
    
    return {
        "max_drawdown_pct": float(drawdown["max_drawdown_pct"]),
        "daily_volatility_pct": float(volatility["daily_volatility_pct"]),
        "annualized_volatility_pct": float(volatility["annualized_volatility_pct"]) if volatility["annualized_volatility_pct"] else None,
        "total_return_pct": float(sharpe["total_return_pct"]),
        "annualized_return_pct": float(sharpe["annualized_return_pct"]),
        "sharpe_ratio": float(sharpe["sharpe_ratio"]) if sharpe["sharpe_ratio"] else None,
    }
