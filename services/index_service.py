"""大盘指数服务 - 带数据库缓存"""
import json
import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict
from decimal import Decimal

from database.connection import get_db_context
from utils.rate_limiter import akshare_limiter

logger = logging.getLogger(__name__)

# A股指数 (新浪接口)
ZH_INDEX_CODES = {
    "sh000001": {"name": "上证指数", "sina_code": "sh000001"},
    "sz399001": {"name": "深证成指", "sina_code": "sz399001"}, 
    "sz399006": {"name": "创业板指", "sina_code": "sz399006"},
    "sh000688": {"name": "科创板指", "sina_code": "sh000688"},
}

# 港股指数 (新浪港股接口)
HK_INDEX_CODES = {
    "HSTECH": {"name": "恒生科技"},
}

# 美股指数 (新浪美股接口，直接返回纳斯达克)
US_INDEX_CODES = {
    "NASDAQ": {"name": "纳斯达克"},
}

# A股交易时间段
MARKET_OPEN_TIME = time(9, 30)
MARKET_CLOSE_TIME = time(15, 0)
# 盘中缓存有效期（秒）
TRADING_CACHE_TTL = 300  # 5分钟


class IndexService:
    """大盘指数服务"""
    
    @staticmethod
    def get_cached_indices() -> Optional[Dict]:
        """从数据库获取缓存的指数数据（返回最近一次的数据，不管是不是今天）"""
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM settings WHERE key = 'market_indices'"
            )
            row = cursor.fetchone()
            
            if not row or not row["value"]:
                return None
            
            try:
                data = json.loads(row["value"])
                return data
            except (json.JSONDecodeError, ValueError):
                return None
    
    @staticmethod
    def save_indices_to_cache(data: Dict) -> None:
        """保存指数数据到数据库缓存"""
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES ('market_indices', %s, %s)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = EXCLUDED.updated_at
            """, (json.dumps(data, ensure_ascii=False), datetime.now()))
    
    @staticmethod
    async def fetch_indices_from_sina() -> List[Dict]:
        """从新浪接口获取大盘指数最新数据
        
        交易时间内使用实时行情接口，非交易时间使用日线数据
        """
        try:
            import akshare as ak
            
            indices = []
            today = date.today()
            is_trading = IndexService._is_trading_time()
            
            # 1. 获取A股指数
            if is_trading:
                # 交易时间内：使用实时行情接口
                try:
                    akshare_limiter.acquire()
                    df = ak.stock_zh_index_spot_sina()
                    
                    if df is not None and not df.empty:
                        for code, info in ZH_INDEX_CODES.items():
                            # 查找对应指数（使用中文列名）
                            mask = df['代码'] == info["sina_code"]
                            result = df[mask]
                            
                            if not result.empty:
                                row = result.iloc[0]
                                price = float(row['最新价'])
                                change = float(row['涨跌额'])
                                change_pct = float(row['涨跌幅'])
                                
                                indices.append({
                                    "code": code,
                                    "name": info["name"],
                                    "price": round(price, 2),
                                    "change": round(change, 2),
                                    "change_pct": round(change_pct, 2),
                                    "date": str(today),
                                })
                except Exception as e:
                    logger.warning(f"获取A股实时指数失败: {e}，尝试使用日线数据")
                    # 降级到日线数据
                    indices = await IndexService._fetch_indices_daily()
                    if indices:
                        return indices
            else:
                # 非交易时间：使用日线数据
                indices = await IndexService._fetch_indices_daily()
                if indices:
                    return indices
            
            # 2. 获取港股指数（使用日线数据，港股交易时间不同）
            for code, info in HK_INDEX_CODES.items():
                try:
                    akshare_limiter.acquire()
                    df = ak.stock_hk_index_daily_sina(symbol=code)
                    
                    if df is not None and not df.empty:
                        last_row = df.iloc[-1]
                        prev_row = df.iloc[-2] if len(df) > 1 else last_row
                        
                        last_close = float(last_row["close"])
                        prev_close = float(prev_row["close"])
                        change = last_close - prev_close
                        change_pct = (change / prev_close * 100) if prev_close != 0 else 0
                        
                        indices.append({
                            "code": code,
                            "name": info["name"],
                            "price": round(last_close, 2),
                            "change": round(change, 2),
                            "change_pct": round(change_pct, 2),
                            "date": str(last_row["date"]),
                        })
                except Exception as e:
                    logger.warning(f"获取 港股指数 {code} 失败: {e}")
                    continue
            
            # 3. 获取美股指数 (纳斯达克)
            try:
                akshare_limiter.acquire()
                df = ak.index_us_stock_sina()
                
                if df is not None and not df.empty:
                    last_row = df.iloc[-1]
                    prev_row = df.iloc[-2] if len(df) > 1 else last_row
                    
                    last_close = float(last_row["close"])
                    prev_close = float(prev_row["close"])
                    change = last_close - prev_close
                    change_pct = (change / prev_close * 100) if prev_close != 0 else 0
                    
                    indices.append({
                        "code": "NASDAQ",
                        "name": "纳斯达克",
                        "price": round(last_close, 2),
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 2),
                        "date": str(last_row["date"]),
                    })
            except Exception as e:
                logger.warning(f"获取 美股指数失败: {e}")
            
            return indices
        except Exception as e:
            logger.error(f"获取大盘指数失败: {e}")
            return []
    
    @staticmethod
    async def _fetch_indices_daily() -> List[Dict]:
        """获取A股指数日线数据（非交易时间使用）"""
        import akshare as ak
        
        indices = []
        for code, info in ZH_INDEX_CODES.items():
            try:
                akshare_limiter.acquire()
                df = ak.stock_zh_index_daily(symbol=info["sina_code"])
                
                if df is not None and not df.empty:
                    last_row = df.iloc[-1]
                    prev_row = df.iloc[-2] if len(df) > 1 else last_row
                    
                    last_close = float(last_row["close"])
                    prev_close = float(prev_row["close"])
                    change = last_close - prev_close
                    change_pct = (change / prev_close * 100) if prev_close != 0 else 0
                    
                    indices.append({
                        "code": code,
                        "name": info["name"],
                        "price": round(last_close, 2),
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 2),
                        "date": str(last_row["date"]),
                    })
            except Exception as e:
                logger.warning(f"获取 A股指数 {code} 日线数据失败: {e}")
                continue
        
        return indices
    
    @staticmethod
    def _is_trading_time() -> bool:
        """判断当前是否在A股交易时间段内 (9:30-15:00)"""
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()
        
        # 周末不交易
        if weekday >= 5:  # 5=周六, 6=周日
            return False
        
        # 检查是否在交易时间段
        return MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME
    
    @staticmethod
    def _is_after_market_close() -> bool:
        """判断当前是否已收盘 (15:00 后)"""
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()
        
        # 周末视为"收盘后"
        if weekday >= 5:
            return True
        
        return current_time >= MARKET_CLOSE_TIME
    
    @staticmethod
    def _is_before_market_open() -> bool:
        """判断当前是否在开盘前 (9:30 前)"""
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()
        
        # 周末视为"开盘前"
        if weekday >= 5:
            return True
        
        return current_time < MARKET_OPEN_TIME
    
    @staticmethod
    def _get_cache_validity(cached: Dict) -> tuple:
        """
        检查缓存数据是否有效，返回 (is_valid, reason)
        
        智能缓存策略：
        - 交易日盘中：缓存5分钟有效
        - 交易日盘后：当日数据一直有效
        - 非交易日：最近交易日数据有效
        """
        if not cached or not cached.get("indices"):
            return False, "no_cache"
        
        cached_date_str = cached.get("date")
        cached_update_time = cached.get("update_time")  # 缓存更新时间戳
        
        if not cached_date_str:
            return False, "no_date"
        
        # 解析缓存数据的日期
        try:
            if "T" in cached_date_str:
                cached_dt = datetime.fromisoformat(cached_date_str)
            else:
                cached_dt = datetime.strptime(cached_date_str, "%Y-%m-%d")
            cached_date_only = cached_dt.date() if isinstance(cached_dt, datetime) else cached_dt
        except (ValueError, TypeError):
            return False, "invalid_date"
        
        now = datetime.now()
        today = now.date()
        
        # 1. 如果是交易日盘中
        if IndexService._is_trading_time():
            # 检查缓存是否是今天的数据
            if cached_date_only != today:
                return False, "trading_time_stale"
            
            # 检查缓存更新时间，5分钟内有效
            if cached_update_time:
                try:
                    update_dt = datetime.fromisoformat(cached_update_time)
                    age = (now - update_dt).total_seconds()
                    if age < TRADING_CACHE_TTL:
                        return True, "trading_time_fresh"
                    else:
                        return False, "trading_time_expired"
                except:
                    pass
            
            # 没有更新时间，视为过期
            return False, "no_update_time"
        
        # 2. 如果是交易日盘后 (15:00 后)
        if IndexService._is_after_market_close():
            # 今天的数据就有效
            if cached_date_only == today:
                return True, "after_market_today"
            # 昨天的数据也勉强可以（可能是刚过零点）
            elif cached_date_only == today - timedelta(days=1):
                return True, "after_market_yesterday"
            else:
                return False, "after_market_stale"
        
        # 3. 如果是交易日盘前 (9:30 前)
        if IndexService._is_before_market_open():
            # 昨天或更早的数据有效（等待开盘）
            if cached_date_only < today:
                return True, "before_market_valid"
            # 今天的数据（可能是刚过零点但有夜盘数据？）也有效
            elif cached_date_only == today:
                return True, "before_market_today"
            else:
                return False, "before_market_future"
        
        # 默认情况：检查是否是最近的有效交易日
        # 简单判断：如果缓存是周五的数据，周末都有效
        weekday = today.weekday()
        if weekday == 5:  # 周六
            if cached_date_only.weekday() == 4:  # 周五
                return True, "weekend_friday"
        elif weekday == 6:  # 周日
            if cached_date_only.weekday() == 4:  # 周五
                return True, "weekend_friday"
        
        return False, "unknown"
    
    @staticmethod
    def save_indices_to_cache(data: Dict) -> None:
        """保存指数数据到数据库缓存"""
        with get_db_context() as conn:
            cursor = conn.cursor()
            # 添加更新时间戳
            data_to_save = {**data, "update_time": datetime.now().isoformat()}
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES ('market_indices', %s, %s)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = EXCLUDED.updated_at
            """, (json.dumps(data_to_save, ensure_ascii=False), datetime.now()))
    
    @staticmethod
    async def get_indices(use_cache: bool = True) -> Dict:
        """获取大盘指数数据
        
        智能缓存策略：
        1. 交易日盘中：缓存5分钟有效
        2. 交易日盘后：当日数据一直有效
        3. 非交易日：最近交易日数据有效
        """
        # 获取缓存数据
        cached = IndexService.get_cached_indices()
        
        # 如果使用缓存，检查缓存有效性
        if use_cache and cached:
            is_valid, reason = IndexService._get_cache_validity(cached)
            
            if is_valid:
                cached_date_str = cached.get("date", "")
                cached_date_only = None
                try:
                    if "T" in cached_date_str:
                        cached_date_only = datetime.fromisoformat(cached_date_str).date()
                    else:
                        cached_date_only = datetime.strptime(cached_date_str, "%Y-%m-%d").date()
                except:
                    pass
                
                today = date.today()
                is_today = cached_date_only == today if cached_date_only else False
                
                logger.debug(f"使用缓存数据: reason={reason}, date={cached_date_str}")
                return {
                    "data": cached["indices"],
                    "cached": True,
                    "is_today": is_today,
                    "date": cached_date_str,
                    "cache_reason": reason
                }
            else:
                logger.debug(f"缓存已过期: reason={reason}")
        
        # 尝试获取新数据
        indices = await IndexService.fetch_indices_from_sina()
        
        if indices:
            # 使用指数数据中的日期
            data_date = indices[0].get("date") if indices else None
            cache_data = {
                "indices": indices,
                "date": data_date or datetime.now().isoformat()
            }
            IndexService.save_indices_to_cache(cache_data)
            
            # 判断数据是否是今天
            today = date.today()
            is_today = False
            if data_date:
                try:
                    data_dt = datetime.strptime(data_date, "%Y-%m-%d")
                    is_today = data_dt.date() == today
                except:
                    pass
            
            return {
                "data": indices,
                "cached": False,
                "is_today": is_today,
                "date": data_date
            }
        
        # 获取失败，尝试返回任何可用的缓存
        if cached and cached.get("indices"):
            return {
                "data": cached["indices"],
                "cached": True,
                "is_today": False,
                "stale": True,
                "date": cached.get("date")
            }
        
        return {
            "data": [],
            "cached": False,
            "error": "无法获取指数数据"
        }