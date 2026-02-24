"""行情数据服务"""
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict
import logging

from database.connection import get_db_context
from utils.rate_limiter import akshare_limiter

logger = logging.getLogger(__name__)


class MarketService:
    """行情数据服务"""
    
    @staticmethod
    def get_prices_from_db(
        fund_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[dict]:
        """从数据库获取历史净值"""
        with get_db_context() as conn:
            sql = "SELECT * FROM prices WHERE fund_code = ?"
            params = [fund_code]
            
            if start_date:
                sql += " AND date >= ?"
                params.append(start_date)
            if end_date:
                sql += " AND date <= ?"
                params.append(end_date)
            
            sql += " ORDER BY date ASC"
            
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_latest_price_date(fund_code: str) -> Optional[date]:
        """获取数据库中最新的净值日期"""
        with get_db_context() as conn:
            cursor = conn.execute(
                "SELECT MAX(date) as max_date FROM prices WHERE fund_code = ?",
                (fund_code,)
            )
            row = cursor.fetchone()
            return row["max_date"] if row and row["max_date"] else None
    
    @staticmethod
    def save_prices(fund_code: str, prices: List[dict]) -> int:
        """保存净值数据到数据库"""
        if not prices:
            return 0
        
        with get_db_context() as conn:
            count = 0
            for p in prices:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO prices 
                        (fund_code, net_value, accum_value, date, growth_rate)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        fund_code,
                        float(p.get("net_value")) if p.get("net_value") is not None else None,
                        float(p.get("accum_value")) if p.get("accum_value") is not None else None,
                        p.get("date"),
                        float(p.get("growth_rate")) if p.get("growth_rate") is not None else None,
                    ))
                    count += 1
                except Exception as e:
                    logger.warning(f"保存净值数据失败: {p.get('date')} - {e}")
            
            return count
    
    @staticmethod
    def update_cache_meta(
        fund_code: str,
        sync_status: str,
        last_sync_date: Optional[date] = None,
        error_message: Optional[str] = None
    ) -> None:
        """更新缓存元数据"""
        with get_db_context() as conn:
            conn.execute("""
                INSERT INTO cache_meta (fund_code, last_sync_date, last_sync_time, sync_status, error_message, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(fund_code) DO UPDATE SET
                    last_sync_date = ?,
                    last_sync_time = ?,
                    sync_status = ?,
                    error_message = ?,
                    updated_at = ?
            """, (
                fund_code, last_sync_date, datetime.now(), sync_status, error_message, datetime.now(),
                last_sync_date, datetime.now(), sync_status, error_message, datetime.now()
            ))
    
    @staticmethod
    def get_cache_meta(fund_code: str) -> Optional[dict]:
        """获取缓存元数据"""
        with get_db_context() as conn:
            cursor = conn.execute(
                "SELECT * FROM cache_meta WHERE fund_code = ?",
                (fund_code,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    async def fetch_fund_info_from_akshare(fund_code: str) -> Optional[dict]:
        """从 AkShare 获取基金基本信息"""
        try:
            import akshare as ak
            
            akshare_limiter.acquire()
            
            # 获取基金列表并查找
            df = ak.fund_name_em()
            result = df[df["基金代码"] == fund_code]
            
            if not result.empty:
                row = result.iloc[0]
                return {
                    "fund_code": fund_code,
                    "fund_name": row.get("基金简称", ""),
                    "fund_type": row.get("基金类型", None),
                }
            
            return None
        except Exception as e:
            logger.error(f"获取基金信息失败 {fund_code}: {e}")
            return None

    @staticmethod
    async def fetch_fund_history_from_akshare(
        fund_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[dict]:
        """从 AkShare 获取历史净值"""
        try:
            import akshare as ak
            
            akshare_limiter.acquire()
            
            # 获取历史净值数据 (AkShare API 更新: fund -> symbol, indicator 默认值变化)
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            
            prices = []
            for _, row in df.iterrows():
                try:
                    price_date = row["净值日期"]
                    if isinstance(price_date, str):
                        price_date = datetime.strptime(price_date, "%Y-%m-%d").date()
                    
                    # 日期过滤
                    if start_date and price_date < start_date:
                        continue
                    if end_date and price_date > end_date:
                        continue
                    
                    # 处理日增长率（可能是字符串带%或已经是数值）
                    growth_rate = None
                    if "日增长率" in row and row["日增长率"] is not None:
                        gr_val = row["日增长率"]
                        if isinstance(gr_val, str):
                            growth_rate = Decimal(gr_val.replace("%", ""))
                        else:
                            growth_rate = Decimal(str(gr_val))
                    
                    prices.append({
                        "date": price_date,
                        "net_value": Decimal(str(row["单位净值"])),
                        "accum_value": None,  # 新版API不返回累计净值
                        "growth_rate": growth_rate,
                    })
                except Exception as e:
                    logger.warning(f"解析净值数据失败: {row} - {e}")
                    continue
            
            return prices
        except Exception as e:
            logger.error(f"获取历史净值失败 {fund_code}: {e}")
            return []

    @staticmethod
    async def sync_fund_history(fund_code: str, force: bool = False) -> dict:
        """同步基金历史净值（增量更新）"""
        # 获取本地最新日期
        latest_date = MarketService.get_latest_price_date(fund_code)
        today = date.today()
        
        # 计算需要获取的开始日期
        if force or not latest_date:
            start_date = None  # 获取全部历史
        else:
            start_date = latest_date + timedelta(days=1)
        
        # 如果开始日期大于今天，无需更新
        if start_date and start_date > today:
            return {
                "fund_code": fund_code,
                "status": "skipped",
                "message": "数据已是最新"
            }
        
        # 更新同步状态
        MarketService.update_cache_meta(fund_code, "pending")
        
        try:
            # 获取数据
            prices = await MarketService.fetch_fund_history_from_akshare(
                fund_code, start_date, today
            )
            
            if prices:
                # 保存到数据库
                count = MarketService.save_prices(fund_code, prices)
                
                # 更新基金的最新净值信息
                latest_price = prices[-1]
                from services.fund_service import FundService
                FundService.update_fund(
                    fund_code,
                    last_price_date=latest_price["date"],
                    last_net_value=float(latest_price["net_value"]) if latest_price["net_value"] else None,
                    last_growth_rate=float(latest_price.get("growth_rate")) if latest_price.get("growth_rate") else None
                )
            else:
                count = 0
            
            # 更新同步状态
            MarketService.update_cache_meta(fund_code, "synced", today)
            
            return {
                "fund_code": fund_code,
                "status": "success",
                "count": count,
                "latest_date": prices[-1]["date"] if prices else latest_date
            }
        except Exception as e:
            error_msg = str(e)
            MarketService.update_cache_meta(fund_code, "failed", error_message=error_msg)
            logger.error(f"同步基金历史失败 {fund_code}: {e}")
            return {
                "fund_code": fund_code,
                "status": "failed",
                "error": error_msg
            }

    @staticmethod
    async def search_funds(keyword: str, limit: int = 20) -> List[dict]:
        """搜索基金"""
        try:
            import akshare as ak
            
            akshare_limiter.acquire()
            
            df = ak.fund_name_em()
            
            # 搜索匹配
            mask = (
                df["基金代码"].str.contains(keyword, na=False) |
                df["基金简称"].str.contains(keyword, na=False)
            )
            result = df[mask].head(limit)
            
            return [
                {
                    "fund_code": row["基金代码"],
                    "fund_name": row["基金简称"],
                    "fund_type": row.get("基金类型", ""),
                }
                for _, row in result.iterrows()
            ]
        except Exception as e:
            logger.error(f"搜索基金失败: {e}")
            return []

    @staticmethod
    def get_chart_data(
        fund_code: str,
        period: str = "1m"
    ) -> dict:
        """获取图表数据"""
        # 计算日期范围
        end_date = date.today()
        period_map = {
            "3m": 90,
            "6m": 180,
            "1y": 365,
            "3y": 1095,
            "5y": 1825,
            "all": None
        }
        
        days = period_map.get(period, 30)
        if days:
            start_date = end_date - timedelta(days=days)
        else:
            start_date = None
        
        # 获取数据
        prices = MarketService.get_prices_from_db(fund_code, start_date, end_date)
        
        if not prices:
            return {
                "fund_code": fund_code,
                "dates": [],
                "values": [],
                "indicators": {}
            }
        
        # 提取数据
        dates = [p["date"] for p in prices]
        values = [float(p["net_value"]) for p in prices]
        
        # 计算技术指标
        from utils.indicators import calculate_ma, calculate_macd, calculate_rsi
        from decimal import Decimal
        
        price_decimals = [Decimal(str(v)) for v in values]
        
        indicators = {
            "ma5": [float(v) if v else None for v in calculate_ma(price_decimals, 5)],
            "ma10": [float(v) if v else None for v in calculate_ma(price_decimals, 10)],
            "ma20": [float(v) if v else None for v in calculate_ma(price_decimals, 20)],
        }
        
        macd = calculate_macd(price_decimals)
        indicators["macd"] = {
            "dif": [float(v) for v in macd["dif"]],
            "dea": [float(v) for v in macd["dea"]],
            "macd": [float(v) for v in macd["macd"]]
        }
        
        rsi = calculate_rsi(price_decimals, 14)
        indicators["rsi"] = [float(v) if v else None for v in rsi]
        
        return {
            "fund_code": fund_code,
            "dates": dates,
            "values": values,
            "indicators": indicators
        }
