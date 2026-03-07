"""大盘指数服务 - 带数据库缓存"""
import json
import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict
from decimal import Decimal

from database.connection import get_db_context
from utils.rate_limiter import akshare_limiter

logger = logging.getLogger(__name__)

# 所有可选指数定义 (用户可从中选择6个展示)
# A股指数 (新浪接口)
ZH_INDEX_CODES = {
    "sh000001": {"name": "上证指数", "sina_code": "sh000001", "category": "A股"},
    "sz399001": {"name": "深证成指", "sina_code": "sz399001", "category": "A股"}, 
    "sz399006": {"name": "创业板指", "sina_code": "sz399006", "category": "A股"},
    "sh000688": {"name": "科创50", "sina_code": "sh000688", "category": "A股"},
    "sh000300": {"name": "沪深300", "sina_code": "sh000300", "category": "A股"},
    "sh000905": {"name": "中证500", "sina_code": "sh000905", "category": "A股"},
    "sh000016": {"name": "上证50", "sina_code": "sh000016", "category": "A股"},
    "sh000852": {"name": "中证1000", "sina_code": "sh000852", "category": "A股"},
    "sz399673": {"name": "创业板50", "sina_code": "sz399673", "category": "A股"},
    "sh000019": {"name": "上证180", "sina_code": "sh000019", "category": "A股"},
    "sh000010": {"name": "上证380", "sina_code": "sh000010", "category": "A股"},
    "sz399005": {"name": "中小板指", "sina_code": "sz399005", "category": "A股"},
}

# 港股指数 (新浪港股接口)
HK_INDEX_CODES = {
    "HSI": {"name": "恒生指数", "category": "港股"},
    "HSTECH": {"name": "恒生科技", "category": "港股"},
    "HSCEI": {"name": "国企指数", "category": "港股"},
    "HSHCI": {"name": "恒生医疗保健", "category": "港股"},
}

# 美股指数 (新浪美股接口 - 仅支持纳斯达克)
US_INDEX_CODES = {
    "NASDAQ": {"name": "纳斯达克", "category": "美股"},
}

# 合并所有指数，方便查询
ALL_INDICES = {**ZH_INDEX_CODES, **HK_INDEX_CODES, **US_INDEX_CODES}

# 默认展示的6个指数
DEFAULT_SELECTED_INDICES = ["sh000001", "sz399001", "sz399006", "sh000688", "HSI", "NASDAQ"]

# 用户指数选择的设置key
USER_INDICES_SETTING_KEY = "user_selected_indices"

# 港股交易时间段
HK_MARKET_OPEN_MORNING = time(9, 30)
HK_MARKET_CLOSE_MORNING = time(12, 0)
HK_MARKET_OPEN_AFTERNOON = time(13, 0)
HK_MARKET_CLOSE_AFTERNOON = time(16, 0)

# A股交易时间段
MARKET_OPEN_TIME = time(9, 30)
MARKET_CLOSE_TIME = time(15, 0)
# 盘中缓存有效期（秒）
TRADING_CACHE_TTL = 300  # 5分钟


class IndexService:
    """大盘指数服务"""
    
    @staticmethod
    def get_available_indices() -> List[Dict]:
        """获取所有可选指数列表（用于前端选择器）"""
        indices = []
        for code, info in ALL_INDICES.items():
            indices.append({
                "code": code,
                "name": info["name"],
                "category": info["category"]
            })
        # 按类别排序：A股 -> 港股 -> 美股
        category_order = {"A股": 1, "港股": 2, "美股": 3}
        indices.sort(key=lambda x: (category_order.get(x["category"], 99), x["name"]))
        return indices
    
    @staticmethod
    def get_user_selected_indices() -> List[str]:
        """获取用户选择的指数代码列表"""
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM settings WHERE key = %s",
                (USER_INDICES_SETTING_KEY,)
            )
            row = cursor.fetchone()
            
            if row and row["value"]:
                try:
                    data = json.loads(row["value"])
                    codes = data.get("codes", [])
                    # 验证选择的指数是否有效
                    valid_codes = [c for c in codes if c in ALL_INDICES]
                    # 如果有有效选择，返回它们（即使有些被过滤掉了）
                    if valid_codes:
                        return valid_codes
                except (json.JSONDecodeError, ValueError):
                    pass
            
            # 返回默认选择
            return DEFAULT_SELECTED_INDICES
    
    @staticmethod
    def save_user_selected_indices(codes: List[str]) -> bool:
        """保存用户选择的指数
        
        Args:
            codes: 最多6个指数代码列表
            
        Returns:
            是否保存成功
        """
        # 验证数量
        if len(codes) > 6:
            codes = codes[:6]
        
        # 验证有效性
        valid_codes = [c for c in codes if c in ALL_INDICES]
        if not valid_codes:
            return False
        
        with get_db_context() as conn:
            cursor = conn.cursor()
            data = {"codes": valid_codes}
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = EXCLUDED.updated_at
            """, (USER_INDICES_SETTING_KEY, json.dumps(data, ensure_ascii=False), datetime.now()))
        
        return True
    
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
    async def fetch_indices_from_sina(selected_codes: List[str] = None) -> List[Dict]:
        """从新浪接口获取大盘指数最新数据
        
        Args:
            selected_codes: 用户选择的指数代码列表，如果为空则使用用户保存的配置或默认值
            
        Returns:
            指数数据列表
        """
        try:
            import akshare as ak
            
            # 确定要获取的指数
            if selected_codes is None:
                selected_codes = IndexService.get_user_selected_indices()
            
            # 过滤出各类指数
            zh_codes = [c for c in selected_codes if c in ZH_INDEX_CODES]
            hk_codes = [c for c in selected_codes if c in HK_INDEX_CODES]
            us_codes = [c for c in selected_codes if c in US_INDEX_CODES]
            
            indices = []
            today = date.today()
            is_trading = IndexService._is_trading_time()
            
            # 1. 获取A股指数
            if zh_codes:
                if is_trading:
                    # 交易时间内：使用实时行情接口
                    try:
                        akshare_limiter.acquire()
                        df = ak.stock_zh_index_spot_sina()
                        
                        if df is not None and not df.empty:
                            for code in zh_codes:
                                info = ZH_INDEX_CODES[code]
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
                        zh_indices = await IndexService._fetch_selected_indices_daily(zh_codes)
                        indices.extend(zh_indices)
                else:
                    # 非交易时间：使用日线数据
                    zh_indices = await IndexService._fetch_selected_indices_daily(zh_codes)
                    indices.extend(zh_indices)
            
            # 2. 获取港股指数（使用实时行情接口）
            if hk_codes:
                try:
                    akshare_limiter.acquire()
                    hk_df = ak.stock_hk_index_spot_sina()
                    
                    if hk_df is not None and not hk_df.empty:
                        for code in hk_codes:
                            info = HK_INDEX_CODES[code]
                            mask = hk_df['代码'] == code
                            result = hk_df[mask]
                            
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
                            else:
                                logger.warning(f"港股指数 {code} 未找到")
                except Exception as e:
                    logger.warning(f"获取港股指数失败: {e}")
            
            # 3. 获取美股指数（纳斯达克）
            if us_codes:
                try:
                    akshare_limiter.acquire()
                    df = ak.index_us_stock_sina()
                    
                    if df is not None and not df.empty:
                        # index_us_stock_sina 返回纳斯达克历史数据
                        # 使用最后一行作为最新数据
                        last_row = df.iloc[-1]
                        prev_row = df.iloc[-2] if len(df) > 1 else last_row
                        
                        last_close = float(last_row["close"])
                        prev_close = float(prev_row["close"])
                        change = last_close - prev_close
                        change_pct = (change / prev_close * 100) if prev_close != 0 else 0
                        
                        # 只添加 NASDAQ（akshare 只支持纳斯达克）
                        if "NASDAQ" in us_codes:
                            indices.append({
                                "code": "NASDAQ",
                                "name": "纳斯达克",
                                "price": round(last_close, 2),
                                "change": round(change, 2),
                                "change_pct": round(change_pct, 2),
                                "date": str(last_row["date"]),
                            })
                except Exception as e:
                    logger.warning(f"获取美股指数失败: {e}")
            
            # 按用户选择的顺序排序返回
            code_order = {code: i for i, code in enumerate(selected_codes)}
            indices.sort(key=lambda x: code_order.get(x["code"], 999))
            
            return indices
        except Exception as e:
            logger.error(f"获取大盘指数失败: {e}")
            return []
    
    @staticmethod
    async def _fetch_selected_indices_daily(selected_codes: List[str]) -> List[Dict]:
        """获取指定A股指数的日线数据（非交易时间使用）"""
        import akshare as ak
        
        indices = []
        for code in selected_codes:
            if code not in ZH_INDEX_CODES:
                continue
            info = ZH_INDEX_CODES[code]
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
        # 获取用户选择的指数代码
        selected_codes = IndexService.get_user_selected_indices()
        
        # 获取缓存数据
        cached = IndexService.get_cached_indices()
        
        # 如果使用缓存，检查缓存有效性
        if use_cache and cached:
            # 检查缓存的指数选择是否与当前选择一致
            cached_codes = cached.get("selected_codes", [])
            if set(cached_codes) != set(selected_codes):
                logger.debug("用户选择的指数已变化，需要重新获取")
            else:
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
                        "update_time": cached.get("update_time"),
                        "cache_reason": reason
                    }
                else:
                    logger.debug(f"缓存已过期: reason={reason}")
        
        # 尝试获取新数据
        indices = await IndexService.fetch_indices_from_sina(selected_codes)
        
        if indices:
            # 使用指数数据中的日期
            data_date = indices[0].get("date") if indices else None
            update_time = datetime.now().isoformat()
            cache_data = {
                "indices": indices,
                "date": data_date or datetime.now().isoformat(),
                "selected_codes": selected_codes,  # 保存用户选择
                "update_time": update_time
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
                "date": data_date,
                "update_time": update_time
            }
        
        # 获取失败，尝试返回任何可用的缓存
        if cached and cached.get("indices"):
            return {
                "data": cached["indices"],
                "cached": True,
                "is_today": False,
                "stale": True,
                "date": cached.get("date"),
                "update_time": cached.get("update_time")
            }
        
        return {
            "data": [],
            "cached": False,
            "error": "无法获取指数数据"
        }