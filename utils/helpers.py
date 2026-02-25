"""工具函数"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from database.connection import get_db_context

# .env 文件路径
ENV_FILE_PATH = Path(__file__).parent.parent / ".env"

# 加载 .env 文件
load_dotenv(ENV_FILE_PATH)

# 环境变量映射
ENV_SETTINGS = {
    "deepseek_api_key": "DEEPSEEK_API_KEY",
    "deepseek_base_url": "DEEPSEEK_BASE_URL",
    "deepseek_model": "DEEPSEEK_MODEL",
}


def _read_env_file() -> dict:
    """读取 .env 文件内容，返回键值对字典"""
    env_vars = {}
    if ENV_FILE_PATH.exists():
        with open(ENV_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip()
    return env_vars


def _write_env_file(env_vars: dict) -> None:
    """将键值对字典写入 .env 文件"""
    lines = []
    
    # 数据库配置
    lines.append("# PostgreSQL 数据库配置")
    lines.append("")
    db_keys = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    for key in db_keys:
        if key in env_vars:
            lines.append(f"{key}={env_vars[key]}")
    lines.append("")
    
    # 写入 DeepSeek API 配置
    lines.append("# DeepSeek API 配置")
    lines.append("")
    
    api_keys = ["DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"]
    comments = {
        "DEEPSEEK_API_KEY": "API Key",
        "DEEPSEEK_BASE_URL": "API 地址",
        "DEEPSEEK_MODEL": "模型",
    }
    
    for key in api_keys:
        if key in env_vars:
            value = env_vars[key]
            if key in comments:
                lines.append(f"# {comments[key]}")
            lines.append(f"{key}={value}")
            lines.append("")
    
    # 写入其他未在顺序中的变量
    for key, value in env_vars.items():
        if key not in db_keys and key not in api_keys:
            lines.append(f"{key}={value}")
    
    with open(ENV_FILE_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def get_setting(key: str) -> Optional[str]:
    """获取设置值，优先从环境变量读取"""
    # 先检查是否有环境变量映射
    env_key = ENV_SETTINGS.get(key)
    if env_key:
        env_value = os.getenv(env_key)
        if env_value:
            return env_value
    
    # 否则从数据库读取
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT value FROM settings WHERE key = %s", (key,)
        )
        row = cursor.fetchone()
        return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    """设置值到数据库"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value, updated_at) 
            VALUES (%s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = %s
        """, (key, value, datetime.now(), value, datetime.now()))


def set_env_setting(key: str, value: Optional[str]) -> None:
    """设置环境变量并保存到 .env 文件"""
    env_key = ENV_SETTINGS.get(key)
    if not env_key:
        return
    
    # 读取现有配置
    env_vars = _read_env_file()
    
    if value:
        env_vars[env_key] = value
        os.environ[env_key] = value
    elif env_key in env_vars:
        del env_vars[env_key]
        os.environ.pop(env_key, None)
    
    # 写入文件
    _write_env_file(env_vars)


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
