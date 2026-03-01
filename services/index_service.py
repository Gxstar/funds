"""大盘指数服务 - 带数据库缓存"""
import json
import logging
from datetime import datetime, date
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
        """从新浪接口获取大盘指数最新数据（更稳定）"""
        try:
            import akshare as ak
            
            indices = []
            
            # 1. 获取A股指数
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
                    logger.warning(f"获取 A股指数 {code} 失败: {e}")
                    continue
            
            # 2. 获取港股指数
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
    async def get_indices(use_cache: bool = True) -> Dict:
        """获取大盘指数数据
        
        逻辑：
        1. 如果有缓存数据，检查日期
        2. 如果缓存是最新交易日数据，直接返回
        3. 否则尝试获取新数据，失败则返回旧缓存
        """
        # 获取缓存数据
        cached = IndexService.get_cached_indices()
        
        # 如果使用缓存且有缓存数据
        if use_cache and cached and cached.get("indices"):
            cached_date = cached.get("date")
            if cached_date:
                # 尝试解析日期
                try:
                    if "T" in cached_date:
                        cached_dt = datetime.fromisoformat(cached_date)
                    else:
                        cached_dt = datetime.strptime(cached_date, "%Y-%m-%d")
                    
                    # 获取今天的日期
                    today = date.today()
                    cached_date_only = cached_dt.date() if isinstance(cached_dt, datetime) else cached_dt
                    
                    # 判断是否需要更新（工作日且不是同一天）
                    # 简单判断：如果缓存日期是今天，或者今天是周末且缓存是周五，则不需要更新
                    weekday = today.weekday()  # 0=周一, 6=周日
                    need_update = True
                    
                    if cached_date_only == today:
                        need_update = False
                    elif weekday == 5:  # 周六
                        # 如果缓存是周五的数据，不需要更新
                        if cached_date_only.weekday() == 4:  # 周五
                            need_update = False
                    elif weekday == 6:  # 周日
                        # 如果缓存是周五的数据，不需要更新
                        if cached_date_only.weekday() == 4:  # 周五
                            need_update = False
                    
                    if not need_update:
                        is_today = cached_date_only == today
                        return {
                            "data": cached["indices"],
                            "cached": True,
                            "is_today": is_today,
                            "date": cached_date
                        }
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"解析缓存日期失败: {e}")
        
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
    
    @staticmethod
    def get_holding_change_stats(holdings: List[Dict]) -> Dict:
        """计算持仓涨跌统计"""
        if not holdings:
            return {
                "total": 0,
                "up": 0,
                "down": 0,
                "flat": 0,
                "avg_change": 0
            }
        
        up = down = flat = 0
        total_change = 0
        
        for fund in holdings:
            rate = fund.get("last_growth_rate")
            if rate is None:
                flat += 1
            elif float(rate) > 0:
                up += 1
                total_change += float(rate)
            elif float(rate) < 0:
                down += 1
                total_change += float(rate)
            else:
                flat += 1
        
        total = len(holdings)
        avg_change = total_change / total if total > 0 else 0
        
        return {
            "total": total,
            "up": up,
            "down": down,
            "flat": flat,
            "avg_change": round(avg_change, 2)
        }