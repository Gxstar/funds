"""数据库连接管理"""
import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# 加载 .env 文件
load_dotenv()

# PostgreSQL 连接参数
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "funds")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


def get_db():
    """获取数据库连接"""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )
    # 设置客户端编码
    conn.set_client_encoding('UTF8')
    return conn


@contextmanager
def get_db_context() -> Generator:
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
        cursor = conn.cursor()
        
        # 基金基础信息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS funds (
                id SERIAL PRIMARY KEY,
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                id SERIAL PRIMARY KEY,
                fund_code VARCHAR(6) NOT NULL,
                total_shares DECIMAL(18,4) NOT NULL,
                cost_price DECIMAL(10,4) NOT NULL,
                total_cost DECIMAL(18,2) NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
            )
        """)
        
        # 交易记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
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
                FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
            )
        """)
        
        # 历史净值缓存表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id SERIAL PRIMARY KEY,
                fund_code VARCHAR(6) NOT NULL,
                net_value DECIMAL(10,4) NOT NULL,
                accum_value DECIMAL(10,4),
                date DATE NOT NULL,
                growth_rate DECIMAL(8,4),
                UNIQUE(fund_code, date),
                FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
            )
        """)
        
        # 缓存元数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_meta (
                id SERIAL PRIMARY KEY,
                fund_code VARCHAR(6) NOT NULL UNIQUE,
                last_sync_date DATE,
                last_sync_time TIMESTAMP,
                sync_status VARCHAR(20),
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
            )
        """)
        
        # 设置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id SERIAL PRIMARY KEY,
                key VARCHAR(50) UNIQUE NOT NULL,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_fund_code ON prices(fund_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_fund_code ON trades(fund_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date)")
        
        # 初始化默认设置
        default_settings = [
            ("deepseek_api_key", ""),
            ("deepseek_base_url", "https://api.deepseek.com/v1"),
            ("deepseek_model", "deepseek-chat"),
        ]
        for key, value in default_settings:
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO NOTHING
            """, (key, value))