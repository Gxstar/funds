"""数据库连接管理"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

DB_PATH = Path(__file__).parent.parent / "data" / "funds.db"


def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    # 启用外键约束
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db_context() -> Generator[sqlite3.Connection, None, None]:
    """数据库连接上下文管理器"""
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """初始化数据库表结构"""
    with get_db_context() as conn:
        # 基金基础信息表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS funds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_code VARCHAR(6) UNIQUE NOT NULL,
                fund_name VARCHAR(100) NOT NULL,
                fund_type VARCHAR(50),
                risk_level VARCHAR(10),
                last_price_date DATE,
                last_net_value DECIMAL(10,4),
                last_growth_rate DECIMAL(8,4),
                info_updated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 当前持仓表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_code VARCHAR(6) NOT NULL,
                total_shares DECIMAL(18,4) NOT NULL,
                cost_price DECIMAL(10,4) NOT NULL,
                total_cost DECIMAL(18,2) NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fund_code) REFERENCES funds(fund_code)
            )
        """)
        
        # 交易记录表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_code VARCHAR(6) NOT NULL,
                trade_type VARCHAR(4) NOT NULL,
                trade_date DATE NOT NULL,
                confirm_date DATE,
                confirm_shares DECIMAL(18,4),
                confirm_net_value DECIMAL(10,4),
                shares DECIMAL(18,4),
                price DECIMAL(10,4),
                amount DECIMAL(18,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fund_code) REFERENCES funds(fund_code)
            )
        """)
        
        # 历史净值缓存表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_code VARCHAR(6) NOT NULL,
                net_value DECIMAL(10,4) NOT NULL,
                accum_value DECIMAL(10,4),
                date DATE NOT NULL,
                growth_rate DECIMAL(8,4),
                UNIQUE(fund_code, date),
                FOREIGN KEY (fund_code) REFERENCES funds(fund_code)
            )
        """)
        
        # 缓存元数据表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_code VARCHAR(6) NOT NULL UNIQUE,
                last_sync_date DATE,
                last_sync_time TIMESTAMP,
                sync_status VARCHAR(20),
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fund_code) REFERENCES funds(fund_code)
            )
        """)
        
        # 设置表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key VARCHAR(50) UNIQUE NOT NULL,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prices_fund_code ON prices(fund_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_fund_code ON trades(fund_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date)")
        
        # 数据库迁移：为 trades 表添加新字段
        try:
            conn.execute("ALTER TABLE trades ADD COLUMN confirm_date DATE")
        except sqlite3.OperationalError:
            pass  # 字段已存在
        try:
            conn.execute("ALTER TABLE trades ADD COLUMN confirm_shares DECIMAL(18,4)")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE trades ADD COLUMN confirm_net_value DECIMAL(10,4)")
        except sqlite3.OperationalError:
            pass
        
        # 初始化默认设置
        default_settings = [
            ("deepseek_api_key", ""),
            ("deepseek_base_url", "https://api.deepseek.com/v1"),
            ("deepseek_model", "deepseek-chat"),
        ]
        for key, value in default_settings:
            conn.execute("""
                INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
            """, (key, value))
