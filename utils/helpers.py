"""工具函数"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any
import json

from database.connection import get_db_context


def get_setting(key: str) -> Optional[str]:
    """获取设置值"""
    with get_db_context() as conn:
        cursor = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    """设置值"""
    with get_db_context() as conn:
        conn.execute("""
            INSERT INTO settings (key, value, updated_at) 
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?
        """, (key, value, datetime.now(), value, datetime.now()))


def format_decimal(value: Decimal, places: int = 2) -> str:
    """格式化小数"""
    return f"{value:.{places}f}"


def format_currency(value: Decimal) -> str:
    """格式化货币"""
    return f"¥{value:,.2f}"


def format_percent(value: Decimal) -> str:
    """格式化百分比"""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def parse_date(date_str: str) -> Optional[date]:
    """解析日期字符串"""
    if not date_str:
        return None
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def calculate_profit(
    shares: Decimal,
    cost_price: Decimal,
    current_price: Decimal
) -> tuple[Decimal, Decimal]:
    """计算盈亏
    返回: (盈亏金额, 盈亏比例)
    """
    cost = shares * cost_price
    current_value = shares * current_price
    profit = current_value - cost
    profit_rate = (profit / cost * 100) if cost else Decimal("0")
    return profit, profit_rate


def get_trade_days(start_date: date, end_date: date) -> list[date]:
    """获取交易日期列表（简化版，不含节假日判断）"""
    from datetime import timedelta
    days = []
    current = start_date
    while current <= end_date:
        # 跳过周末
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days
