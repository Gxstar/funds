"""AI 分析服务"""
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import logging
import httpx

from utils.helpers import get_setting, get_total_position_amount

logger = logging.getLogger(__name__)


ANALYSIS_PROMPT = """你是一位专业的基金投资顾问。请根据以下数据分析该基金的投资建议。

## 基金基本信息
- 基金名称: {fund_name}
- 基金代码: {fund_code}
- 基金类型: {fund_type}
- 风险等级: {risk_level}

## 技术指标数据
- 当前净值: {current_value}
- 近5日涨跌幅: {change_5d}%
- 近20日涨跌幅: {change_20d}%
- MA5: {ma5}
- MA10: {ma10}
- MA20: {ma20}
- RSI(14): {rsi}
- MACD: {macd}

## 持仓信息（如有）
{holding_info}

## 仓位信息
{position_info}

## 请回答
1. 当前技术面分析（趋势判断、支撑压力位）
2. 买卖建议（强烈买入/买入/持有/卖出/强烈卖出）
3. 建议理由（分点说明，简洁明了）
4. 风险提示
5. 仓位建议（基于当前仓位比例给出加减仓建议）

请用简洁专业的语言回答，不要过于冗长。回复格式使用 Markdown。
"""


class DeepSeekClient:
    """DeepSeek API 客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = 60.0
    
    async def chat(
        self,
        messages: List[dict],
        model: str = "deepseek-chat",
        temperature: float = 0.7
    ) -> str:
        """调用 DeepSeek Chat API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature
                }
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]


class AIService:
    """AI 分析服务"""
    
    @staticmethod
    def get_client() -> Optional[DeepSeekClient]:
        """获取 DeepSeek 客户端"""
        api_key = get_setting("deepseek_api_key")
        if not api_key:
            return None
        
        base_url = get_setting("deepseek_base_url") or "https://api.deepseek.com/v1"
        return DeepSeekClient(api_key, base_url)
    
    @staticmethod
    def is_configured() -> bool:
        """检查 AI 是否已配置"""
        return bool(get_setting("deepseek_api_key"))
    
    @staticmethod
    async def analyze_fund(fund_code: str) -> dict:
        """分析单只基金"""
        client = AIService.get_client()
        if not client:
            return {
                "fund_code": fund_code,
                "error": "DeepSeek API 未配置，请在设置中配置 API Key"
            }
        
        # 获取基金数据
        from services.fund_service import FundService
        from services.market_service import MarketService
        
        fund = FundService.get_fund_by_code(fund_code)
        if not fund:
            return {
                "fund_code": fund_code,
                "error": "基金不存在"
            }
        
        # 获取图表数据（包含技术指标）
        chart_data = MarketService.get_chart_data(fund_code, "6m")
        
        # 准备分析数据
        values = chart_data["values"]
        indicators = chart_data.get("indicators", {})
        
        # 计算涨跌幅
        change_5d = 0
        change_20d = 0
        if len(values) >= 5:
            change_5d = (values[-1] - values[-5]) / values[-5] * 100
        if len(values) >= 20:
            change_20d = (values[-1] - values[-20]) / values[-20] * 100
        
        # 获取最新的指标值
        def get_latest(arr):
            if not arr:
                return None
            for v in reversed(arr):
                if v is not None:
                    return round(v, 4)
            return None
        
        # 持仓信息
        holding = FundService.get_holding(fund_code)
        if holding:
            shares = Decimal(str(holding["total_shares"]))
            cost_price = Decimal(str(holding["cost_price"]))
            current_value = Decimal(str(fund.get("last_net_value") or 0))
            market_value = shares * current_value
            profit = market_value - Decimal(str(holding["total_cost"]))
            profit_rate = (profit / Decimal(str(holding["total_cost"])) * 100) if holding["total_cost"] else Decimal("0")
            
            holding_info = f"""- 持有份额: {shares:.2f}
- 成本价: {cost_price:.4f}
- 当前市值: {market_value:.2f}
- 盈亏金额: {profit:.2f}
- 盈亏比例: {profit_rate:.2f}%"""
        else:
            holding_info = "暂无持仓"
        
        # 仓位信息
        total_position = get_total_position_amount()
        if total_position > 0:
            # 获取总市值
            from services.fund_service import FundService
            summary = FundService.get_holdings_summary()
            total_market_value = Decimal(str(summary.get("total_market_value", 0)))
            position_ratio = float(total_market_value / total_position * 100) if total_position else 0
            available = total_position - total_market_value
            
            position_info = f"""- 满仓金额: ¥{float(total_position):,.2f}
- 当前市值: ¥{float(total_market_value):,.2f}
- 仓位比例: {position_ratio:.1f}%
- 剩余可用: ¥{float(available):,.2f}"""
        else:
            position_info = "未设置满仓金额（可在设置中配置）"
        
        # 构建提示词
        prompt = ANALYSIS_PROMPT.format(
            fund_name=fund.get("fund_name", ""),
            fund_code=fund_code,
            fund_type=fund.get("fund_type", "未知"),
            risk_level=fund.get("risk_level", "未知"),
            current_value=values[-1] if values else 0,
            change_5d=round(change_5d, 2),
            change_20d=round(change_20d, 2),
            ma5=get_latest(indicators.get("ma5", [])),
            ma10=get_latest(indicators.get("ma10", [])),
            ma20=get_latest(indicators.get("ma20", [])),
            rsi=get_latest(indicators.get("rsi", [])),
            macd=get_latest(indicators.get("macd", {}).get("macd", [])),
            holding_info=holding_info,
            position_info=position_info
        )
        
        try:
            model = get_setting("deepseek_model") or "deepseek-chat"
            analysis = await client.chat([
                {"role": "system", "content": "你是专业的基金投资顾问，擅长技术分析和量化分析。"},
                {"role": "user", "content": prompt}
            ], model=model)
            
            return {
                "fund_code": fund_code,
                "analysis": analysis,
                "indicators": {
                    "ma5": get_latest(indicators.get("ma5", [])),
                    "ma10": get_latest(indicators.get("ma10", [])),
                    "ma20": get_latest(indicators.get("ma20", [])),
                    "rsi": get_latest(indicators.get("rsi", [])),
                    "macd": get_latest(indicators.get("macd", {}).get("macd", [])),
                },
                "change_5d": round(change_5d, 2),
                "change_20d": round(change_20d, 2),
                "timestamp": datetime.now().isoformat()
            }
        except httpx.HTTPStatusError as e:
            error_msg = f"API 请求失败: {e.response.status_code}"
            if e.response.status_code == 401:
                error_msg = "API Key 无效，请检查配置"
            elif e.response.status_code == 429:
                error_msg = "API 请求频率超限，请稍后重试"
            
            logger.error(f"AI 分析失败: {e}")
            return {
                "fund_code": fund_code,
                "error": error_msg
            }
        except Exception as e:
            logger.error(f"AI 分析失败: {e}")
            return {
                "fund_code": fund_code,
                "error": f"分析失败: {str(e)}"
            }
    
    @staticmethod
    async def analyze_portfolio() -> dict:
        """分析持仓组合"""
        from services.fund_service import FundService
        
        # 获取所有持仓
        holdings_summary = FundService.get_holdings_summary()
        
        if holdings_summary["fund_count"] == 0:
            return {
                "error": "暂无持仓"
            }
        
        # 获取各基金详情
        funds = FundService.get_all_funds()
        holdings = [f for f in funds if f.get("total_shares")]
        
        # 汇总分析
        results = []
        for fund in holdings:
            result = await AIService.analyze_fund(fund["fund_code"])
            results.append(result)
            # 避免请求过快
            await asyncio.sleep(1)
        
        return {
            "summary": holdings_summary,
            "analyses": results,
            "timestamp": datetime.now().isoformat()
        }
