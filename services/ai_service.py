"""AI 分析服务"""
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List
import logging
import httpx
import json
from pathlib import Path

from utils.helpers import get_setting, get_total_position_amount
from database.connection import get_db_context

logger = logging.getLogger(__name__)

# 提示词配置文件路径
PROMPTS_FILE = Path(__file__).parent.parent / "config" / "prompts.json"


def load_prompts() -> dict:
    """加载提示词配置"""
    try:
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载提示词配置失败: {e}")
        return {}


def get_fund_analysis_prompts() -> tuple:
    """获取基金分析提示词"""
    prompts = load_prompts()
    fund_prompts = prompts.get("fund_analysis", {})
    return (
        fund_prompts.get("system_prompt", "你是专业的基金投资顾问，擅长技术分析和量化分析。"),
        fund_prompts.get("user_prompt", "")
    )


def get_portfolio_analysis_prompts() -> tuple:
    """获取持仓组合分析提示词"""
    prompts = load_prompts()
    portfolio_prompts = prompts.get("portfolio_analysis", {})
    return (
        portfolio_prompts.get("system_prompt", "你是专业的基金投资顾问，擅长投资组合分析和资产配置。"),
        portfolio_prompts.get("user_prompt", "")
    )


class AICache:
    """AI 分析缓存管理"""
    
    @staticmethod
    def get_cache(fund_code: str, analysis_type: str = "fund") -> Optional[dict]:
        """获取缓存的分析结果"""
        try:
            with get_db_context() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, analysis, indicators, risk_metrics, created_at
                    FROM ai_analysis 
                    WHERE fund_code = %s AND analysis_type = %s
                """, (fund_code, analysis_type))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return {
                    "id": row.get("id"),
                    "analysis": row.get("analysis"),
                    "indicators": row.get("indicators"),
                    "risk_metrics": row.get("risk_metrics"),
                    "timestamp": row.get("created_at").isoformat() if row.get("created_at") else None,
                    "cached": True
                }
        except Exception as e:
            logger.error(f"获取AI缓存失败: {e}")
            return None
    
    @staticmethod
    def save_cache(fund_code: str, analysis: str, analysis_type: str = "fund", 
                   indicators: dict = None, risk_metrics: dict = None) -> None:
        """保存分析结果到缓存（始终只保存最新的一条）"""
        try:
            now = datetime.now()
            
            with get_db_context() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ai_analysis (fund_code, analysis_type, analysis, indicators, risk_metrics, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (fund_code, analysis_type) 
                    DO UPDATE SET 
                        analysis = EXCLUDED.analysis,
                        indicators = EXCLUDED.indicators,
                        risk_metrics = EXCLUDED.risk_metrics,
                        created_at = EXCLUDED.created_at
                """, (fund_code, analysis_type, analysis, 
                      json.dumps(indicators) if indicators else None,
                      json.dumps(risk_metrics) if risk_metrics else None,
                      now))
                logger.info(f"已保存AI缓存: {fund_code}")
        except Exception as e:
            logger.error(f"保存AI缓存失败: {e}")
    
    @staticmethod
    def clear_cache(fund_code: str, analysis_type: str = "fund") -> None:
        """清除缓存"""
        try:
            with get_db_context() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM ai_analysis WHERE fund_code = %s AND analysis_type = %s
                """, (fund_code, analysis_type))
        except Exception as e:
            logger.error(f"清除AI缓存失败: {e}")
    
    @staticmethod
    def is_cache_valid(fund_code: str, analysis_type: str = "fund") -> bool:
        """检查缓存是否存在"""
        cache = AICache.get_cache(fund_code, analysis_type)
        return cache is not None


class DeepSeekClient:
    """DeepSeek API 客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = 120.0  # 增加到 120 秒
    
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
            
            # 检查响应格式
            if "choices" not in result or len(result["choices"]) == 0:
                logger.error(f"API 响应格式异常: {result}")
                raise ValueError("API 响应格式异常")
            
            content = result["choices"][0].get("message", {}).get("content")
            if not content:
                logger.error(f"API 响应内容为空: {result}")
                raise ValueError("API 响应内容为空")
            
            return content


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
    async def analyze_fund(fund_code: str, force_refresh: bool = False, cache_only: bool = False) -> dict:
        """分析单只基金
        
        Args:
            fund_code: 基金代码
            force_refresh: 是否强制刷新缓存（重新分析）
            cache_only: 只获取缓存，没有缓存时返回空
        """
        # 如果不是强制刷新，先尝试获取缓存
        if not force_refresh:
            cache = AICache.get_cache(fund_code, "fund")
            if cache:
                logger.info(f"使用缓存的AI分析: {fund_code}")
                return {
                    "fund_code": fund_code,
                    "analysis": cache["analysis"],
                    "indicators": cache.get("indicators", {}),
                    "risk_metrics": cache.get("risk_metrics"),
                    "timestamp": cache["timestamp"],
                    "cached": True
                }
        
        # 如果只获取缓存且没有缓存，返回空
        if cache_only:
            return {
                "fund_code": fund_code,
                "analysis": None,
                "cached": False,
                "no_cache": True
            }
        
        client = AIService.get_client()
        if not client:
            return {
                "fund_code": fund_code,
                "error": "DeepSeek API 未配置，请在设置中配置 API Key"
            }
        
        # 获取基金数据
        from services.fund_service import FundService
        from services.market_service import MarketService
        from services.market_sentiment_service import MarketSentimentService
        from services.fund_detail_service import FundDetailService, ValuationService
        from utils.indicators import calculate_risk_metrics
        from decimal import Decimal
        import asyncio
        
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
        
        # 计算风险指标
        risk_metrics = None
        if len(values) >= 20:
            try:
                price_decimals = [Decimal(str(v)) for v in values]
                risk_metrics = calculate_risk_metrics(price_decimals)
            except Exception as e:
                logger.warning(f"计算风险指标失败: {e}")
        
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
            summary = FundService.get_holdings_summary()
            total_market_value = Decimal(str(summary.get("total_market_value", 0)))
            position_ratio = float(total_market_value / total_position * 100) if total_position else 0
            available = total_position - total_market_value
            
            # 计算该基金在组合中的占比
            fund_ratio_in_portfolio = 0
            if total_market_value > 0 and holding:
                shares = Decimal(str(holding["total_shares"]))
                current_value = Decimal(str(fund.get("last_net_value") or 0))
                fund_market_value = shares * current_value
                fund_ratio_in_portfolio = float(fund_market_value / total_market_value * 100)
            
            position_info = f"""- 满仓金额: ¥{float(total_position):,.2f}
- 账户总市值: ¥{float(total_market_value):,.2f}
- 账户仓位比例: {position_ratio:.1f}%
- 剩余可用资金: ¥{float(available):,.2f}
- 该基金占组合比例: {fund_ratio_in_portfolio:.1f}%"""
        else:
            position_info = "未设置满仓金额（可在设置中配置）"
        
        # 获取关联 ETF 数据
        etf_info = "暂无关联 ETF"
        etf_data = None
        related_etf = fund.get("related_etf")
        
        if related_etf:
            try:
                from services.etf_service import ETFService
                etf_data = await ETFService.get_etf_analysis_data(related_etf)
                
                if etf_data and etf_data.get("available"):
                    realtime = etf_data.get("realtime", {})
                    money_flow = etf_data.get("money_flow", {})
                    
                    etf_info = f"""- 关联 ETF: {related_etf} ({realtime.get('name', '-')})
- 当日价格: {realtime.get('current_price', '-')}
- 当日涨跌幅: {realtime.get('change_pct', 0):.2f}%
- 今开: {realtime.get('open', '-')} | 最高: {realtime.get('high', '-')} | 最低: {realtime.get('low', '-')}
- 昨收: {realtime.get('pre_close', '-')}"""
                    
                    if money_flow:
                        main_inflow = money_flow.get('main_net_inflow', 0)
                        main_inflow_pct = money_flow.get('main_net_inflow_pct', 0)
                        etf_info += f"""
- 主力净流入: {main_inflow:,.0f} 元 ({main_inflow_pct:.2f}%)"""
                    
                    if realtime.get('is_trading'):
                        etf_info += "\n- 状态: 交易中（实时数据）"
                    else:
                        etf_info += "\n- 状态: 非交易时间（最近收盘数据）"
            except Exception as e:
                logger.error(f"获取 ETF 数据失败: {e}")
                etf_info = f"关联 ETF {related_etf} 数据获取失败"
        
        # 获取市场情绪数据
        try:
            sentiment_data = await MarketSentimentService.get_market_sentiment()
            market_sentiment_info = MarketSentimentService.format_sentiment_for_ai(sentiment_data)
        except Exception as e:
            logger.warning(f"获取市场情绪失败: {e}")
            market_sentiment_info = "市场情绪数据暂不可用"
        
        # 获取基金详情
        try:
            fund_detail = await FundDetailService.get_fund_detail(fund_code)
            fund_detail_info = FundDetailService.format_detail_for_ai(fund_detail)
        except Exception as e:
            logger.warning(f"获取基金详情失败: {e}")
            fund_detail_info = "基金详情数据暂不可用"
        
        # 获取相关新闻
        try:
            from services.news_service import NewsService
            etf_name = None
            if etf_data and etf_data.get("realtime"):
                etf_name = etf_data["realtime"].get("name")
            news_list = await NewsService.get_fund_related_news(
                fund_type=fund.get("fund_type"),
                related_etf_name=etf_name,
                max_news=3
            )
            news_info = NewsService.format_news_for_ai(news_list)
        except Exception as e:
            logger.warning(f"获取新闻失败: {e}")
            news_info = "相关新闻暂不可用"
        
        # 获取用户交易历史（近10笔）
        try:
            trades = FundService.get_trades(fund_code, limit=10)
            if trades:
                trade_list = []
                for t in trades:
                    trade_type = "买入" if t["trade_type"] == "BUY" else "卖出"
                    trade_date = t["trade_date"]
                    amount = float(t.get("amount", 0))
                    shares = float(t.get("confirm_shares", 0)) if t.get("confirm_shares") else 0
                    nav = float(t.get("confirm_net_value", 0)) if t.get("confirm_net_value") else 0
                    trade_list.append(f"- {trade_date} {trade_type}: ¥{amount:,.0f} ({shares:.2f}份, 净值{nav:.4f})")
                trade_history = "\n".join(trade_list)
            else:
                trade_history = "暂无交易记录"
        except Exception as e:
            logger.warning(f"获取交易历史失败: {e}")
            trade_history = "交易历史暂不可用"
        
        # 格式化风险指标
        risk_info = "风险指标数据不足"
        if risk_metrics:
            risk_info = f"""- 最大回撤: {risk_metrics['max_drawdown_pct']:.2f}%
- 日波动率: {risk_metrics['daily_volatility_pct']:.2f}%
- 年化波动率: {risk_metrics['annualized_volatility_pct']:.2f}%" if risk_metrics.get('annualized_volatility_pct') else "- 年化波动率: 数据不足"
- 近6月总收益: {risk_metrics['total_return_pct']:.2f}%
- 年化收益率: {risk_metrics['annualized_return_pct']:.2f}%
- 夏普比率: {risk_metrics['sharpe_ratio']:.2f}" if risk_metrics.get('sharpe_ratio') else "- 夏普比率: 数据不足\""""
        
        # 从配置文件加载提示词
        system_prompt, user_prompt_template = get_fund_analysis_prompts()
        
        # 构建提示词
        prompt = user_prompt_template.format(
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
            etf_info=etf_info,
            holding_info=holding_info,
            position_info=position_info,
            market_sentiment=market_sentiment_info,
            fund_detail=fund_detail_info,
            risk_metrics=risk_info,
            related_news=news_info,
            trade_history=trade_history
        )
        
        try:
            model = get_setting("deepseek_model") or "deepseek-chat"
            analysis = await client.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ], model=model)
            
            # 构建结果
            indicators_data = {
                "ma5": get_latest(indicators.get("ma5", [])),
                "ma10": get_latest(indicators.get("ma10", [])),
                "ma20": get_latest(indicators.get("ma20", [])),
                "rsi": get_latest(indicators.get("rsi", [])),
                "macd": get_latest(indicators.get("macd", {}).get("macd", [])),
            }
            
            # 保存到缓存
            AICache.save_cache(
                fund_code=fund_code,
                analysis=analysis,
                analysis_type="fund",
                indicators=indicators_data,
                risk_metrics=risk_metrics
            )
            
            return {
                "fund_code": fund_code,
                "analysis": analysis,
                "indicators": indicators_data,
                "risk_metrics": risk_metrics,
                "change_5d": round(change_5d, 2),
                "change_20d": round(change_20d, 2),
                "timestamp": datetime.now().isoformat(),
                "cached": False
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
        except httpx.TimeoutException as e:
            logger.error(f"AI 分析超时: {e}")
            return {
                "fund_code": fund_code,
                "error": "API 请求超时，请稍后重试"
            }
        except Exception as e:
            logger.error(f"AI 分析失败: {type(e).__name__}: {e}")
            return {
                "fund_code": fund_code,
                "error": f"分析失败: {str(e) or type(e).__name__}"
            }
    
    @staticmethod
    async def analyze_portfolio(force_refresh: bool = False, cache_only: bool = False) -> dict:
        """分析持仓组合（整体分析）
        
        Args:
            force_refresh: 是否强制刷新缓存（重新分析）
            cache_only: 只获取缓存，没有缓存时返回空
        """
        from services.fund_service import FundService
        from services.market_service import MarketService
        
        # 如果不是强制刷新，先尝试获取缓存
        if not force_refresh:
            cache = AICache.get_cache("portfolio", "portfolio")
            if cache:
                logger.info("使用缓存的持仓分析")
                return {
                    "analysis": cache["analysis"],
                    "summary": cache.get("indicators", {}),
                    "timestamp": cache["timestamp"],
                    "cached": True
                }
        
        # 如果只获取缓存且没有缓存，返回空
        if cache_only:
            return {
                "analysis": None,
                "cached": False,
                "no_cache": True
            }
        
        client = AIService.get_client()
        if not client:
            return {
                "error": "DeepSeek API 未配置，请在设置中配置 API Key"
            }
        
        # 获取所有持仓汇总
        holdings_summary = FundService.get_holdings_summary()
        
        if holdings_summary["fund_count"] == 0:
            return {
                "error": "暂无持仓"
            }
        
        # 获取各基金详情
        funds = FundService.get_all_funds()
        holdings = [f for f in funds if f.get("total_shares") and float(f.get("total_shares", 0)) > 0]
        
        # 获取总仓位设置
        total_position = get_total_position_amount()
        total_market_value = Decimal(str(holdings_summary.get("total_market_value", 0)))
        position_ratio = float(total_market_value / total_position * 100) if total_position else 0
        available = total_position - total_market_value if total_position else Decimal("0")
        
        # 构建账户汇总信息
        account_summary = f"""- 持有基金数量: {holdings_summary['fund_count']} 只
- 总投入成本: ¥{float(holdings_summary['total_cost']):,.2f}
- 当前总市值: ¥{float(holdings_summary['total_market_value']):,.2f}
- 总盈亏: ¥{float(holdings_summary['total_profit']):,.2f} ({float(holdings_summary['profit_rate']):.2f}%)
- 满仓金额: ¥{float(total_position):,.2f}
- 账户仓位: {position_ratio:.1f}%
- 剩余可用: ¥{float(available):,.2f}"""
        
        # 构建各基金持仓明细
        holdings_detail_list = []
        for fund in holdings:
            fund_code = fund["fund_code"]
            fund_name = fund.get("fund_name", fund_code)
            shares = float(fund.get("total_shares", 0))
            cost_price = float(fund.get("cost_price", 0))
            total_cost = float(fund.get("total_cost", 0))
            last_net_value = float(fund.get("last_net_value") or 0)
            last_growth_rate = float(fund.get("last_growth_rate") or 0)
            fund_type = fund.get("fund_type", "未知")
            
            market_value = shares * last_net_value if last_net_value else 0
            profit = market_value - total_cost
            profit_rate = (profit / total_cost * 100) if total_cost else 0
            ratio_in_portfolio = (market_value / float(total_market_value) * 100) if float(total_market_value) else 0
            
            # 获取近期涨跌幅
            try:
                chart_data = MarketService.get_chart_data(fund_code, "1m")
                values = chart_data.get("values", [])
                change_5d = 0
                change_20d = 0
                if len(values) >= 5:
                    change_5d = (values[-1] - values[-5]) / values[-5] * 100
                if len(values) >= 20:
                    change_20d = (values[-1] - values[-20]) / values[-20] * 100
            except:
                change_5d = 0
                change_20d = 0
            
            holdings_detail_list.append(f"""### {fund_name} ({fund_code})
- 类型: {fund_type}
- 持有份额: {shares:.2f}
- 成本价: {cost_price:.4f}
- 当前净值: {last_net_value:.4f}
- 当前市值: ¥{market_value:,.2f}
- 盈亏: ¥{profit:,.2f} ({profit_rate:.2f}%)
- 占组合比例: {ratio_in_portfolio:.1f}%
- 近5日涨跌: {change_5d:.2f}%
- 近20日涨跌: {change_20d:.2f}%""")
        
        holdings_detail = "\n\n".join(holdings_detail_list)
        
        # 获取市场指数数据
        from services.index_service import IndexService
        market_indices_data = await IndexService.get_indices(use_cache=True)
        market_indices = "暂无数据"
        if market_indices_data.get("data"):
            indices_list = []
            for idx in market_indices_data["data"]:
                change_str = f"+{idx['change_pct']:.2f}%" if idx['change_pct'] > 0 else f"{idx['change_pct']:.2f}%"
                indices_list.append(f"- {idx['name']}: {idx['price']:.2f} ({change_str})")
            market_indices = "\n".join(indices_list)
            if market_indices_data.get("date"):
                market_indices += f"\n\n数据日期: {market_indices_data['date']}"
        
        # 获取市场情绪数据
        from services.market_sentiment_service import MarketSentimentService
        try:
            sentiment_data = await MarketSentimentService.get_market_sentiment()
            market_sentiment = f"""- 涨跌家数: {sentiment_data.get('up_count', 0)} 涨 / {sentiment_data.get('down_count', 0)} 跌
- 涨跌比: {sentiment_data.get('up_down_ratio', 'N/A')}
- 北向资金: {sentiment_data.get('north_flow', 'N/A')}
- 市场强度: {sentiment_data.get('market_strength', 'N/A')}"""
        except Exception as e:
            logger.warning(f"获取市场情绪失败: {e}")
            market_sentiment = "暂无数据"
        
        # 获取相关新闻（综合各板块新闻）
        from services.news_service import NewsService
        try:
            # 获取综合财经新闻
            all_news = await NewsService.get_fund_related_news(max_news=10)
            if all_news:
                news_list = []
                for news in all_news[:10]:
                    news_list.append(f"- [{news.get('source', '财经')}] {news.get('title', '')}")
                related_news = "\n".join(news_list)
            else:
                related_news = "暂无相关新闻"
        except Exception as e:
            logger.warning(f"获取新闻失败: {e}")
            related_news = "暂无相关新闻"
        
        # 获取账户交易历史汇总（近20笔）
        try:
            all_trades = FundService.get_trades(limit=20)
            if all_trades:
                # 统计买入卖出情况
                buy_count = sum(1 for t in all_trades if t["trade_type"] == "BUY")
                sell_count = sum(1 for t in all_trades if t["trade_type"] == "SELL")
                buy_amount = sum(float(t.get("amount", 0)) for t in all_trades if t["trade_type"] == "BUY")
                sell_amount = sum(float(t.get("amount", 0)) for t in all_trades if t["trade_type"] == "SELL")
                
                # 构建交易明细
                trade_list = []
                for t in all_trades[:15]:  # 显示最近15笔
                    trade_type = "买入" if t["trade_type"] == "BUY" else "卖出"
                    fund_name = t.get("fund_name", t["fund_code"])[:10]
                    trade_list.append(f"- {t['trade_date']} {fund_name} {trade_type}: ¥{float(t.get('amount', 0)):,.0f}")
                
                trade_summary = f"""### 交易统计（近{len(all_trades)}笔）
- 买入次数: {buy_count} 次，合计 ¥{buy_amount:,.0f}
- 卖出次数: {sell_count} 次，合计 ¥{sell_amount:,.0f}
- 净买入: ¥{buy_amount - sell_amount:,.0f}

### 最近交易明细
{chr(10).join(trade_list)}"""
            else:
                trade_summary = "暂无交易记录"
        except Exception as e:
            logger.warning(f"获取交易历史失败: {e}")
            trade_summary = "交易历史暂不可用"
        
        # 从配置文件加载提示词
        system_prompt, user_prompt_template = get_portfolio_analysis_prompts()
        
        # 构建提示词
        prompt = user_prompt_template.format(
            market_indices=market_indices,
            market_sentiment=market_sentiment,
            account_summary=account_summary,
            holdings_detail=holdings_detail,
            related_news=related_news,
            trade_summary=trade_summary,
            available_amount=float(available)
        )
        
        try:
            model = get_setting("deepseek_model") or "deepseek-chat"
            analysis = await client.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ], model=model)
            
            # 保存摘要数据用于缓存
            summary = {
                "fund_count": holdings_summary['fund_count'],
                "total_cost": float(holdings_summary['total_cost']),
                "total_market_value": float(holdings_summary['total_market_value']),
                "total_profit": float(holdings_summary['total_profit']),
                "profit_rate": float(holdings_summary['profit_rate']),
                "position_ratio": position_ratio
            }
            
            # 保存到缓存
            AICache.save_cache(
                fund_code="portfolio",
                analysis=analysis,
                analysis_type="portfolio",
                indicators=summary
            )
            
            return {
                "analysis": analysis,
                "summary": summary,
                "timestamp": datetime.now().isoformat(),
                "cached": False
            }
        except httpx.HTTPStatusError as e:
            error_msg = f"API 请求失败: {e.response.status_code}"
            if e.response.status_code == 401:
                error_msg = "API Key 无效，请检查配置"
            elif e.response.status_code == 429:
                error_msg = "API 请求频率超限，请稍后重试"
            
            logger.error(f"AI 分析失败: {e}")
            return {
                "error": error_msg
            }
        except httpx.TimeoutException as e:
            logger.error(f"AI 分析超时: {e}")
            return {
                "error": "API 请求超时，请稍后重试"
            }
        except Exception as e:
            logger.error(f"AI 分析失败: {type(e).__name__}: {e}")
            return {
                "error": f"分析失败: {str(e) or type(e).__name__}"
            }
