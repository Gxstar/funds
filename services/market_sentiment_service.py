"""市场情绪服务 - 使用 akshare 获取数据"""
from datetime import datetime, date, timedelta
from typing import Optional, Dict
import logging
import threading
import asyncio

logger = logging.getLogger(__name__)


class MarketSentimentCache:
    """市场情绪数据缓存"""
    
    def __init__(self):
        self._data: Dict = {}
        self._timestamp: Optional[datetime] = None
        self._lock = threading.Lock()
        self.CACHE_TTL = 300  # 5 分钟缓存
    
    def get(self) -> Optional[Dict]:
        with self._lock:
            if not self._data or not self._timestamp:
                return None
            age = (datetime.now() - self._timestamp).total_seconds()
            if age < self.CACHE_TTL:
                return self._data
            return None
    
    def set(self, data: Dict):
        with self._lock:
            self._data = data
            self._timestamp = datetime.now()


# 全局缓存实例
sentiment_cache = MarketSentimentCache()


class MarketSentimentService:
    """市场情绪服务 - 基于 akshare"""
    
    # 主要指数代码映射（腾讯接口格式）
    INDEX_MAPPING = {
        "上证指数": "sh000001",
        "深证成指": "sz399001",
        "创业板指": "sz399006",
        "沪深300": "sh000300",
        "中证500": "sh000905",
        "科创50": "sh000688",
    }
    
    @staticmethod
    async def get_market_sentiment() -> Dict:
        """获取市场情绪数据（大盘涨跌统计、北向资金等）"""
        # 检查缓存
        cached = sentiment_cache.get()
        if cached:
            return cached
        
        result = {
            "market_breadth": None,  # 涨跌家数
            "north_flow": None,  # 北向资金
            "index_data": None,  # 主要指数
            "update_time": datetime.now().isoformat()
        }
        
        try:
            # 并行获取数据
            market_breadth, north_flow, index_data = await asyncio.gather(
                MarketSentimentService._get_market_breadth(),
                MarketSentimentService._get_north_flow(),
                MarketSentimentService._get_index_data(),
                return_exceptions=True
            )
            
            if not isinstance(market_breadth, Exception):
                result["market_breadth"] = market_breadth
            if not isinstance(north_flow, Exception):
                result["north_flow"] = north_flow
            if not isinstance(index_data, Exception):
                result["index_data"] = index_data
            
            # 缓存结果
            sentiment_cache.set(result)
            
        except Exception as e:
            logger.error(f"获取市场情绪数据失败: {e}")
        
        return result
    
    @staticmethod
    async def _get_market_breadth() -> Optional[Dict]:
        """获取大盘涨跌家数统计 - 使用 akshare"""
        try:
            # 在线程池中运行同步的 akshare 调用
            loop = asyncio.get_event_loop()
            
            def _fetch_stock_data():
                import akshare as ak
                # 获取所有A股实时行情
                df = ak.stock_zh_a_spot_em()
                return df
            
            df = await loop.run_in_executor(None, _fetch_stock_data)
            
            if df is None or df.empty:
                return None
            
            up_count = 0  # 上涨
            down_count = 0  # 下跌
            flat_count = 0  # 平盘
            limit_up = 0  # 涨停
            limit_down = 0  # 跌停
            
            # 遍历统计
            for _, row in df.iterrows():
                change_pct = row.get('涨跌幅', 0)
                if change_pct is None:
                    continue
                try:
                    change_pct = float(change_pct)
                except (ValueError, TypeError):
                    continue
                    
                if change_pct > 0:
                    up_count += 1
                    if change_pct >= 9.8:
                        limit_up += 1
                elif change_pct < 0:
                    down_count += 1
                    if change_pct <= -9.8:
                        limit_down += 1
                else:
                    flat_count += 1
            
            total = up_count + down_count + flat_count
            
            if total < 1000:  # 数据不足
                logger.warning(f"涨跌家数数据不足: {total}")
                return None
            
            up_ratio = (up_count / total * 100) if total > 0 else 0
            
            return {
                "up_count": up_count,
                "down_count": down_count,
                "flat_count": flat_count,
                "limit_up": limit_up,
                "limit_down": limit_down,
                "total": total,
                "up_ratio": round(up_ratio, 1),
                "description": MarketSentimentService._describe_market_breadth(up_count, down_count, total),
                "source": "akshare"
            }
                
        except Exception as e:
            logger.error(f"获取大盘涨跌统计失败: {e}")
            return None
    
    @staticmethod
    def _describe_market_breadth(up_count: int, down_count: int, total: int) -> str:
        """根据涨跌家数描述市场情绪"""
        if total == 0:
            return "数据不足"
        
        up_ratio = up_count / total * 100
        
        if up_ratio >= 80:
            return "市场普涨，情绪极度乐观（注意追高风险）"
        elif up_ratio >= 60:
            return "市场多数上涨，情绪偏乐观"
        elif up_ratio >= 40:
            return "市场涨跌互现，情绪中性"
        elif up_ratio >= 20:
            return "市场多数下跌，情绪偏悲观"
        else:
            return "市场普跌，情绪极度悲观（可能存在反弹机会）"
    
    @staticmethod
    async def _get_north_flow() -> Optional[Dict]:
        """获取北向资金流向 - 使用 akshare"""
        try:
            loop = asyncio.get_event_loop()
            
            def _fetch_north_flow():
                import akshare as ak
                # 获取北向资金历史数据（最近一天）
                df = ak.stock_hsgt_hist_em(symbol="北向资金")
                return df
            
            df = await loop.run_in_executor(None, _fetch_north_flow)
            
            if df is None or df.empty:
                return None
            
            # 获取最新一行数据
            latest = df.iloc[-1]
            
            # 北向资金净流入
            date_str = str(latest.get('日期', ''))
            net_inflow = float(latest.get('当日成交净买额', 0)) if latest.get('当日成交净买额') else 0
            
            return {
                "available": True,
                "net_inflow": net_inflow,
                "date": date_str,
                "description": f"净流入{net_inflow:.2f}亿" if net_inflow >= 0 else f"净流出{abs(net_inflow):.2f}亿"
            }
                
        except Exception as e:
            logger.error(f"获取北向资金失败: {e}")
            return {
                "available": False,
                "message": "北向资金数据暂时不可用",
                "alternative": "可参考港股走势或A50期指作为外资情绪参考"
            }
    
    @staticmethod
    async def _get_index_data() -> Optional[Dict]:
        """获取主要指数数据 - 使用 akshare"""
        try:
            loop = asyncio.get_event_loop()
            
            def _fetch_index_data():
                import akshare as ak
                import httpx
                import re
                
                # 使用腾讯接口获取指数数据（更稳定）
                codes = ",".join(MarketSentimentService.INDEX_MAPPING.values())
                url = f"https://web.sqt.gtimg.cn/q={codes}"
                
                resp = httpx.get(url, timeout=10)
                if resp.status_code != 200:
                    return None
                
                text = resp.text
                indices = {}
                
                for match in re.finditer(r'v_([^=]+)="([^"]+)"', text):
                    code = match.group(1)
                    parts = match.group(2).split('~')
                    
                    if len(parts) > 32:
                        # 找到对应的中文名称
                        name_cn = parts[1]
                        for cn_name, tencent_code in MarketSentimentService.INDEX_MAPPING.items():
                            if tencent_code == code:
                                name_cn = cn_name
                                break
                        
                        indices[code] = {
                            "name": name_cn,
                            "code": code,
                            "price": float(parts[3]) if parts[3] else 0,
                            "change_pct": float(parts[32]) if parts[32] and parts[32] != '-' else 0,
                            "change_amount": float(parts[31]) if parts[31] and parts[31] != '-' else 0,
                            "pre_close": float(parts[4]) if parts[4] else 0,
                        }
                
                return indices
            
            indices = await loop.run_in_executor(None, _fetch_index_data)
            return indices
                
        except Exception as e:
            logger.error(f"获取指数数据失败: {e}")
            return None
    
    @staticmethod
    def format_sentiment_for_ai(sentiment: Dict) -> str:
        """格式化市场情绪数据用于 AI 分析"""
        lines = []
        
        # 主要指数
        index_data = sentiment.get("index_data")
        if index_data:
            lines.append("### 主要指数表现")
            for code, info in index_data.items():
                change_str = f"+{info['change_pct']:.2f}%" if info['change_pct'] > 0 else f"{info['change_pct']:.2f}%"
                lines.append(f"- {info['name']}: {info['price']:.2f} ({change_str})")
        
        # 涨跌家数统计
        market_breadth = sentiment.get("market_breadth")
        if market_breadth:
            lines.append(f"\n### A股涨跌家数")
            
            up_count = market_breadth.get("up_count")
            down_count = market_breadth.get("down_count")
            
            # 只有当 up_count 和 down_count 都有有效值时才显示详细统计
            if up_count is not None and down_count is not None and market_breadth.get("total", 0) > 1000:
                lines.append(f"- 上涨: {up_count} 只")
                lines.append(f"- 下跌: {down_count} 只")
                lines.append(f"- 平盘: {market_breadth.get('flat_count', 0)} 只")
                lines.append(f"- 涨停: {market_breadth.get('limit_up', 0)} 只")
                lines.append(f"- 跌停: {market_breadth.get('limit_down', 0)} 只")
                lines.append(f"- 上涨比例: {market_breadth.get('up_ratio', 0)}%")
                lines.append(f"- 市场情绪: {market_breadth.get('description', '')}")
            else:
                lines.append("- 数据暂不可用，请以指数走势为主要参考")
        
        # 北向资金
        north_flow = sentiment.get("north_flow")
        lines.append(f"\n### 北向资金")
        if north_flow:
            if north_flow.get("available") and north_flow.get("net_inflow") is not None:
                inflow = north_flow.get("net_inflow")
                if inflow >= 0:
                    lines.append(f"- 净流入: +{inflow:.2f} 亿元")
                else:
                    lines.append(f"- 净流出: {abs(inflow):.2f} 亿元")
                lines.append(f"- 日期: {north_flow.get('date', '')}")
            else:
                lines.append(f"- 状态: {north_flow.get('message', '数据暂不可用')}")
                if north_flow.get("alternative"):
                    lines.append(f"- 参考: {north_flow['alternative']}")
        else:
            lines.append("- 数据暂不可用")
        
        if not lines:
            return "市场情绪数据暂不可用"
        
        return "\n".join(lines)
