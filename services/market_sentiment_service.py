"""市场情绪服务 - 使用 akshare 获取数据"""
from datetime import datetime, date, time, timedelta
from typing import Optional, Dict
import logging
import threading
import asyncio
import httpx

logger = logging.getLogger(__name__)

# 请求超时和重试配置
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_DELAY = 1  # 秒

# A股交易时间段
MARKET_OPEN_TIME = time(9, 30)
MARKET_CLOSE_TIME = time(15, 0)
# 盘中缓存有效期（秒）
TRADING_CACHE_TTL = 300  # 5分钟


class MarketSentimentCache:
    """市场情绪数据缓存 - 智能缓存策略"""
    
    def __init__(self):
        self._data: Dict = {}
        self._timestamp: Optional[datetime] = None
        self._lock = threading.Lock()
    
    def _is_trading_time(self) -> bool:
        """判断当前是否在A股交易时间段内"""
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()
        
        if weekday >= 5:  # 周末
            return False
        
        return MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME
    
    def _is_after_market_close(self) -> bool:
        """判断当前是否已收盘"""
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()
        
        if weekday >= 5:
            return True
        
        return current_time >= MARKET_CLOSE_TIME
    
    def _get_cache_ttl(self) -> int:
        """根据时间段动态获取缓存TTL"""
        if self._is_trading_time():
            # 交易时间内，短缓存
            return TRADING_CACHE_TTL
        else:
            # 收盘后或开盘前，使用较长缓存
            # 实际会在 get() 中通过日期判断
            return 3600  # 1小时（兜底值）
    
    def get(self) -> Optional[Dict]:
        """获取缓存数据（智能缓存策略）"""
        with self._lock:
            if not self._data or not self._timestamp:
                return None
            
            now = datetime.now()
            
            # 收盘后：检查是否是同一天的数据
            if self._is_after_market_close():
                cache_date = self._timestamp.date()
                today = now.date()
                if cache_date == today:
                    return self._data
                else:
                    return None
            
            # 交易时间内或开盘前：使用动态TTL
            ttl = self._get_cache_ttl()
            age = (now - self._timestamp).total_seconds()
            
            if age < ttl:
                return self._data
            return None
    
    def set(self, data: Dict):
        with self._lock:
            self._data = data
            self._timestamp = datetime.now()
    
    def clear(self):
        """清除缓存"""
        with self._lock:
            self._data = {}
            self._timestamp = None


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
        """获取大盘涨跌家数统计 - 使用 akshare，带重试机制"""
        loop = asyncio.get_event_loop()
        
        for attempt in range(MAX_RETRIES):
            try:
                def _fetch_stock_data():
                    import akshare as ak
                    # 获取所有A股实时行情
                    df = ak.stock_zh_a_spot_em()
                    return df
                
                # 增加超时时间
                df = await asyncio.wait_for(
                    loop.run_in_executor(None, _fetch_stock_data),
                    timeout=30  # 30秒超时
                )
                
                if df is None or df.empty:
                    continue
                
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
                    continue
                
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
                    
            except asyncio.TimeoutError:
                logger.warning(f"获取大盘涨跌统计超时 (尝试 {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
            except Exception as e:
                logger.warning(f"获取大盘涨跌统计失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {type(e).__name__}: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
        
        # 所有重试都失败，尝试备用方案
        logger.info("尝试使用备用接口获取涨跌家数")
        return await MarketSentimentService._get_market_breadth_fallback()
    
    @staticmethod
    async def _get_market_breadth_fallback() -> Optional[Dict]:
        """备用方案：使用多种方法获取涨跌家数"""
        # 方案1: 尝试分开获取沪深数据（减少单次数据量）
        try:
            result = await MarketSentimentService._get_market_breadth_by_exchange()
            if result:
                return result
        except Exception as e:
            logger.warning(f"分市场获取涨跌家数失败: {e}")
        
        # 方案2: 尝试腾讯财经接口
        try:
            result = await MarketSentimentService._get_market_breadth_tencent()
            if result:
                return result
        except Exception as e:
            logger.warning(f"腾讯接口获取涨跌家数失败: {e}")
        
        # 方案3: 尝试东方财富轻量接口
        try:
            result = await MarketSentimentService._get_market_breadth_eastmoney()
            if result:
                return result
        except Exception as e:
            logger.warning(f"东方财富备用接口获取涨跌家数失败: {e}")
        
        return None
    
    @staticmethod
    async def _get_market_breadth_by_exchange() -> Optional[Dict]:
        """分别获取上海和深圳市场的涨跌家数，减少单次数据量"""
        loop = asyncio.get_event_loop()
        
        def _fetch_sh():
            import akshare as ak
            return ak.stock_sh_a_spot_em()
        
        def _fetch_sz():
            import akshare as ak
            return ak.stock_sz_a_spot_em()
        
        # 并发获取沪深数据
        sh_df, sz_df = await asyncio.gather(
            loop.run_in_executor(None, _fetch_sh),
            loop.run_in_executor(None, _fetch_sz)
        )
        
        up_count = 0
        down_count = 0
        flat_count = 0
        limit_up = 0
        limit_down = 0
        
        for df in [sh_df, sz_df]:
            if df is None or df.empty:
                continue
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
        
        if total < 1000:
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
            "source": "akshare_exchange"
        }
    
    @staticmethod
    async def _get_market_breadth_tencent() -> Optional[Dict]:
        """使用腾讯财经接口获取涨跌家数"""
        loop = asyncio.get_event_loop()
        
        def _fetch_tencent():
            import httpx
            # 腾讯财经市场概况接口
            url = "https://qt.gtimg.cn/q=sh000001,sz399001,sz399006"
            resp = httpx.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            
            # 同时获取涨跌家数统计
            url2 = "https://qt.gtimg.cn/q=hn~shsz~up,hn~shsz~down,hn~shsz~flat"
            resp2 = httpx.get(url2, timeout=10)
            
            if resp2.status_code != 200:
                return None
            
            text = resp2.text
            up_count = 0
            down_count = 0
            flat_count = 0
            
            # 解析腾讯格式的数据
            for line in text.split(';'):
                if 'hn~shsz~up' in line and '"' in line:
                    try:
                        up_count = int(line.split('"')[1])
                    except:
                        pass
                elif 'hn~shsz~down' in line and '"' in line:
                    try:
                        down_count = int(line.split('"')[1])
                    except:
                        pass
                elif 'hn~shsz~flat' in line and '"' in line:
                    try:
                        flat_count = int(line.split('"')[1])
                    except:
                        pass
            
            return up_count, down_count, flat_count
        
        result = await loop.run_in_executor(None, _fetch_tencent)
        if not result:
            return None
        
        up_count, down_count, flat_count = result
        total = up_count + down_count + flat_count
        
        if total < 1000:
            return None
        
        up_ratio = (up_count / total * 100) if total > 0 else 0
        
        return {
            "up_count": up_count,
            "down_count": down_count,
            "flat_count": flat_count,
            "limit_up": None,
            "limit_down": None,
            "total": total,
            "up_ratio": round(up_ratio, 1),
            "description": MarketSentimentService._describe_market_breadth(up_count, down_count, total),
            "source": "tencent"
        }
    
    @staticmethod
    async def _get_market_breadth_eastmoney() -> Optional[Dict]:
        """使用东方财富轻量接口获取涨跌家数"""
        loop = asyncio.get_event_loop()
        
        def _fetch_eastmoney():
            import httpx
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "fid": "f3",
                "po": "1",
                "pz": "5000",
                "pn": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fs": "m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": "f12,f14,f2,f3,f4"
            }
            resp = httpx.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                return None
            return resp.json()
        
        data = await loop.run_in_executor(None, _fetch_eastmoney)
        
        if not data or "data" not in data or "diff" not in data["data"]:
            return None
        
        up_count = 0
        down_count = 0
        flat_count = 0
        
        for item in data["data"]["diff"]:
            change_pct = item.get("f3", 0)
            if change_pct is None:
                continue
            try:
                change_pct = float(change_pct)
            except (ValueError, TypeError):
                continue
            
            if change_pct > 0:
                up_count += 1
            elif change_pct < 0:
                down_count += 1
            else:
                flat_count += 1
        
        total = up_count + down_count + flat_count
        
        if total < 1000:
            return None
        
        up_ratio = (up_count / total * 100) if total > 0 else 0
        
        return {
            "up_count": up_count,
            "down_count": down_count,
            "flat_count": flat_count,
            "limit_up": None,
            "limit_down": None,
            "total": total,
            "up_ratio": round(up_ratio, 1),
            "description": MarketSentimentService._describe_market_breadth(up_count, down_count, total),
            "source": "eastmoney"
        }
    
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
        """获取北向资金流向 - 使用 akshare，带超时处理"""
        try:
            loop = asyncio.get_event_loop()
            
            def _fetch_north_flow():
                import akshare as ak
                # 获取北向资金历史数据（最近一天）
                df = ak.stock_hsgt_hist_em(symbol="北向资金")
                return df
            
            df = await asyncio.wait_for(
                loop.run_in_executor(None, _fetch_north_flow),
                timeout=20  # 20秒超时
            )
            
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
                
        except asyncio.TimeoutError:
            logger.warning("获取北向资金超时")
            return {
                "available": False,
                "message": "北向资金数据请求超时",
                "alternative": "可参考港股走势或A50期指作为外资情绪参考"
            }
        except Exception as e:
            logger.warning(f"获取北向资金失败: {e}")
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
