"""数据库连接管理"""
import os
import sqlite3
from contextlib import contextmanager
from typing import Generator
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 数据库类型
DB_TYPE = os.getenv("DB_TYPE", "postgresql").lower()

# SQLite 配置
SQLITE_PATH = os.getenv("SQLITE_PATH", "data/funds.db")

# PostgreSQL 连接参数
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "funds")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


def get_db():
    """获取数据库连接（支持 SQLite 和 PostgreSQL）"""
    if DB_TYPE == "sqlite":
        # 确保目录存在
        db_path = Path(SQLITE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        # 启用外键支持
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    else:
        # PostgreSQL
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
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
    """初始化数据库表结构（支持 SQLite 和 PostgreSQL）"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        
        is_sqlite = DB_TYPE == "sqlite"
        
        # 根据数据库类型选择 SQL 语法
        if is_sqlite:
            # SQLite 语法
            serial_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
            decimal_type = "REAL"
            timestamp_type = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            unique_constraint = "UNIQUE"
            json_type = "TEXT"  # SQLite 没有 JSONB，用 TEXT 存储 JSON
        else:
            # PostgreSQL 语法
            serial_type = "SERIAL PRIMARY KEY"
            decimal_type = "DECIMAL"
            timestamp_type = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            unique_constraint = "UNIQUE"
            json_type = "JSONB"
        
        # 基金基础信息表
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS funds (
                id {serial_type},
                fund_code VARCHAR(6) {unique_constraint} NOT NULL,
                fund_name VARCHAR(100) NOT NULL,
                fund_type VARCHAR(50),
                risk_level VARCHAR(10),
                related_etf VARCHAR(20),
                last_price_date DATE,
                last_net_value {decimal_type},
                last_growth_rate {decimal_type},
                info_updated_at TIMESTAMP,
                created_at {timestamp_type}
            )
        """)
        
        # 当前持仓表
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS holdings (
                id {serial_type},
                fund_code VARCHAR(6) NOT NULL,
                total_shares {decimal_type} NOT NULL,
                cost_price {decimal_type} NOT NULL,
                total_cost {decimal_type} NOT NULL,
                updated_at {timestamp_type},
                FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
            )
        """)
        
        # 交易记录表
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS trades (
                id {serial_type},
                fund_code VARCHAR(6) NOT NULL,
                trade_type VARCHAR(4) NOT NULL,
                trade_date DATE NOT NULL,
                confirm_date DATE,
                confirm_shares {decimal_type},
                confirm_net_value {decimal_type},
                shares {decimal_type},
                price {decimal_type},
                amount {decimal_type} NOT NULL,
                created_at {timestamp_type},
                FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
            )
        """)
        
        # 历史净值缓存表
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS prices (
                id {serial_type},
                fund_code VARCHAR(6) NOT NULL,
                net_value {decimal_type} NOT NULL,
                accum_value {decimal_type},
                date DATE NOT NULL,
                growth_rate {decimal_type},
                {unique_constraint}(fund_code, date),
                FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
            )
        """)
        
        # 缓存元数据表
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS cache_meta (
                id {serial_type},
                fund_code VARCHAR(6) NOT NULL {unique_constraint},
                last_sync_date DATE,
                last_sync_time TIMESTAMP,
                sync_status VARCHAR(20),
                error_message TEXT,
                created_at {timestamp_type},
                updated_at {timestamp_type},
                FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
            )
        """)
        
        # 设置表
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS settings (
                id {serial_type},
                key VARCHAR(50) {unique_constraint} NOT NULL,
                value TEXT,
                updated_at {timestamp_type}
            )
        """)
        
        # AI 分析缓存表
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS ai_analysis (
                id {serial_type},
                fund_code VARCHAR(20) NOT NULL,
                analysis_type VARCHAR(20) NOT NULL DEFAULT 'fund',
                analysis TEXT NOT NULL,
                indicators {json_type},
                risk_metrics {json_type},
                created_at {timestamp_type},
                {unique_constraint}(fund_code, analysis_type)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_fund_code ON prices(fund_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_fund_code ON trades(fund_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_analysis_fund_code ON ai_analysis(fund_code)")
        
        # 初始化默认设置
        default_settings = [
            ("deepseek_api_key", ""),
            ("deepseek_base_url", "https://api.deepseek.com/v1"),
            ("deepseek_model", "deepseek-chat"),
        ]
        
        for key, value in default_settings:
            if is_sqlite:
                cursor.execute("""
                    INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
                """, (key, value))
            else:
                cursor.execute("""
                    INSERT INTO settings (key, value) VALUES (%s, %s)
                    ON CONFLICT (key) DO NOTHING
                """, (key, value))
        
        # 为现有表添加新字段（如果不存在）- 仅 PostgreSQL
        if not is_sqlite:
            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name = 'funds' AND column_name = 'related_etf') THEN
                        ALTER TABLE funds ADD COLUMN related_etf VARCHAR(20);
                    END IF;
                END $$;
            """)