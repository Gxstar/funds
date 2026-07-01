"""工具函数"""
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional
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
    db_type = os.getenv("DB_TYPE", "postgresql").lower()

    with get_db_context() as conn:
        cursor = conn.cursor()
        if db_type == "sqlite":
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        else:
            cursor.execute("SELECT value FROM settings WHERE key = %s", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    """设置值到数据库"""
    db_type = os.getenv("DB_TYPE", "postgresql").lower()
    now = datetime.now()
    
    with get_db_context() as conn:
        cursor = conn.cursor()
        if db_type == "sqlite":
            # SQLite 语法
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, now))
        else:
            # PostgreSQL 语法
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = %s
            """, (key, value, now, value, now))


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


def get_total_position_amount() -> Decimal:
    """获取满仓金额配置"""
    value = get_setting("total_position_amount")
    if value:
        try:
            return Decimal(value)
        except:
            pass
    return Decimal("0")


def set_total_position_amount(amount: Decimal) -> None:
    """设置满仓金额"""
    set_setting("total_position_amount", str(amount))


# === 交易时间工具 ===

TRADING_MORNING = (time(9, 30), time(11, 30))
TRADING_AFTERNOON = (time(13, 0), time(15, 0))
TRADING_SESSIONS = [TRADING_MORNING, TRADING_AFTERNOON]


def is_trading_day(d: date = None) -> bool:
    """判断是否 A 股交易日（简化：周一至周五，不含法定节假日）"""
    d = d or date.today()
    return d.weekday() < 5


def is_market_open(dt: datetime = None) -> bool:
    """判断当前是否在交易时段内"""
    dt = dt or datetime.now()
    if not is_trading_day(dt.date()):
        return False
    t = dt.time()
    return any(start <= t <= end for start, end in TRADING_SESSIONS)


def is_after_market_close(dt: datetime = None) -> bool:
    """判断是否已收盘（15:00 之后）"""
    dt = dt or datetime.now()
    return dt.time() > TRADING_AFTERNOON[1]


def trading_session_ttl(day_ttl: float = 300, after_hours_ttl: float = 3600) -> float:
    """根据当前时间返回合适的 TTL：盘内短，盘后长"""
    if is_market_open():
        return day_ttl
    return after_hours_ttl
