"""市场情绪服务"""
from datetime import datetime, date, timedelta
from typing import Optional, Dict
import logging
import threading
import httpx
import re

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
    """市场情绪服务"""
    
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
            import asyncio
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
        """获取大盘涨跌家数统计（通过腾讯接口）"""
        try:
            # 使用腾讯接口获取 A 股实时数据统计
            # 这里用一个简化的方法：获取主要指数成分股统计
            url = "https://web.sqt.gtimg.cn/q=sh000001,sz399001,sz399006"
            
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                
                text = resp.text
                # 解析返回数据
                index_info = {}
                for match in re.finditer(r'v_([^=]+)="([^"]+)"', text):
                    code = match.group(1)
                    parts = match.group(2).split('~')
                    if len(parts) > 32:
                        index_info[code] = {
                            "name": parts[1],
                            "price": float(parts[3]) if parts[3] else 0,
                            "change_pct": float(parts[32]) if parts[32] and parts[32] != '-' else 0,
                        }
                
                return {
                    "indices": index_info,
                    "description": MarketSentimentService._describe_market(index_info)
                }
                
        except Exception as e:
            logger.error(f"获取大盘涨跌统计失败: {e}")
            return None
    
    @staticmethod
    def _describe_market(index_info: Dict) -> str:
        """描述市场情绪"""
        if not index_info:
            return "数据获取失败"
        
        up_count = sum(1 for v in index_info.values() if v.get("change_pct", 0) > 0)
        total = len(index_info)
        
        if up_count == total:
            return "市场整体上涨，情绪偏乐观"
        elif up_count == 0:
            return "市场整体下跌，情绪偏悲观"
        elif up_count > total / 2:
            return "市场多数上涨，情绪中性偏多"
        else:
            return "市场多数下跌，情绪中性偏空"
    
    @staticmethod
    async def _get_north_flow() -> Optional[Dict]:
        """获取北向资金流向（通过腾讯接口）"""
        try:
            # 腾讯沪深港通数据
            url = "https://web.sqt.gtimg.cn/q=hk00700,sh000001"
            
            async with httpx.AsyncClient(timeout=10) as client:
                # 尝试从东方财富获取北向资金（备用方案）
                # 由于东方财富接口可能被封，这里用腾讯的港股数据作为代理指标
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                
                # 返回基本信息，实际北向资金需要专用接口
                return {
                    "available": False,
                    "message": "北向资金数据暂时不可用",
                    "alternative": "可参考港股走势作为外资情绪参考"
                }
                
        except Exception as e:
            logger.error(f"获取北向资金失败: {e}")
            return None
    
    @staticmethod
    async def _get_index_data() -> Optional[Dict]:
        """获取主要指数数据"""
        try:
            # 构建请求
            codes = ",".join(MarketSentimentService.INDEX_MAPPING.values())
            url = f"https://web.sqt.gtimg.cn/q={codes}"
            
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
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
        
        # 市场情绪描述
        market_breadth = sentiment.get("market_breadth")
        if market_breadth and market_breadth.get("description"):
            lines.append(f"\n### 市场情绪")
            lines.append(f"- {market_breadth['description']}")
        
        if not lines:
            return "市场情绪数据暂不可用"
        
        return "\n".join(lines)