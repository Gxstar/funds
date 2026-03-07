"""AI 建议路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional
import json

from services.ai_service import AIService, load_prompts, PROMPTS_FILE

router = APIRouter(prefix="/api/ai", tags=["AI建议"])


class SettingsUpdate(BaseModel):
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: Optional[str] = None
    deepseek_model: Optional[str] = None


class PromptsUpdate(BaseModel):
    fund_analysis_system: Optional[str] = None
    fund_analysis_user: Optional[str] = None
    portfolio_analysis_system: Optional[str] = None
    portfolio_analysis_user: Optional[str] = None


class PositionSettingUpdate(BaseModel):
    total_position_amount: Optional[str] = None  # 满仓金额，可选


@router.get("/status")
async def get_ai_status():
    """获取 AI 配置状态"""
    return {
        "configured": AIService.is_configured()
    }


@router.post("/suggest/{fund_code}")
async def suggest_fund(fund_code: str, force_refresh: bool = False, cache_only: bool = False):
    """获取单只基金建议
    
    Args:
        fund_code: 基金代码
        force_refresh: 是否强制刷新缓存
        cache_only: 只获取缓存，没有缓存时返回空
    """
    result = await AIService.analyze_fund(fund_code, force_refresh=force_refresh, cache_only=cache_only)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/suggest/{fund_code}/cache")
async def get_fund_analysis_cache(fund_code: str):
    """获取基金分析的缓存状态"""
    from services.ai_service import AICache
    
    cache = AICache.get_cache(fund_code, "fund")
    if cache:
        return {
            "cached": True,
            "timestamp": cache.get("timestamp"),
            "has_cache": True
        }
    return {
        "cached": False,
        "has_cache": False
    }


@router.delete("/suggest/{fund_code}/cache")
async def clear_fund_analysis_cache(fund_code: str):
    """清除基金分析的缓存"""
    from services.ai_service import AICache
    
    AICache.clear_cache(fund_code, "fund")
    return {"message": "缓存已清除"}


@router.post("/analyze")
async def analyze_portfolio(force_refresh: bool = False, cache_only: bool = False):
    """分析持仓组合
    
    Args:
        force_refresh: 是否强制刷新缓存
        cache_only: 只获取缓存，没有缓存时返回空
    """
    result = await AIService.analyze_portfolio(force_refresh=force_refresh, cache_only=cache_only)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/analyze/cache")
async def get_portfolio_analysis_cache():
    """获取持仓分析的缓存状态"""
    from services.ai_service import AICache
    
    cache = AICache.get_cache("portfolio", "portfolio")
    if cache:
        return {
            "cached": True,
            "timestamp": cache.get("timestamp"),
            "has_cache": True
        }
    return {
        "cached": False,
        "has_cache": False
    }


@router.delete("/analyze/cache")
async def clear_portfolio_analysis_cache():
    """清除持仓分析的缓存"""
    from services.ai_service import AICache
    
    AICache.clear_cache("portfolio", "portfolio")
    return {"message": "缓存已清除"}


@router.get("/settings")
async def get_settings():
    """获取 AI 设置"""
    from utils.helpers import get_setting, get_total_position_amount
    
    api_key = get_setting("deepseek_api_key")
    total_position = get_total_position_amount()
    
    return {
        "api_key_configured": bool(api_key),
        "deepseek_api_key": "***" if api_key else "",
        "deepseek_base_url": get_setting("deepseek_base_url") or "https://api.deepseek.com/v1",
        "deepseek_model": get_setting("deepseek_model") or "deepseek-chat",
        "total_position_amount": str(total_position)
    }


@router.post("/settings")
async def update_settings(settings: SettingsUpdate):
    """更新 AI 设置，保存到 .env 文件"""
    from utils.helpers import set_env_setting
    
    # 只更新非空字符串的设置，避免覆盖已有配置
    if settings.deepseek_api_key:
        set_env_setting("deepseek_api_key", settings.deepseek_api_key)
    if settings.deepseek_base_url:
        set_env_setting("deepseek_base_url", settings.deepseek_base_url)
    if settings.deepseek_model:
        set_env_setting("deepseek_model", settings.deepseek_model)
    
    return {"message": "设置已保存"}


@router.get("/position-setting")
async def get_position_setting():
    """获取仓位设置"""
    from utils.helpers import get_total_position_amount
    
    total_position = get_total_position_amount()
    return {
        "total_position_amount": str(total_position)
    }


@router.post("/position-setting")
async def update_position_setting(setting: PositionSettingUpdate):
    """更新仓位设置"""
    from utils.helpers import set_total_position_amount
    
    # 如果传入空值，清除仓位设置
    if not setting.total_position_amount or not setting.total_position_amount.strip():
        set_total_position_amount(Decimal("0"))
        return {"message": "仓位设置已清除", "total_position_amount": "0"}
    
    try:
        amount = Decimal(setting.total_position_amount.strip())
        if amount < 0:
            raise ValueError("金额不能为负数")
        set_total_position_amount(amount)
        return {"message": "仓位设置已保存", "total_position_amount": str(amount)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/market-sentiment")
async def get_market_sentiment():
    """获取市场情绪数据"""
    from services.market_sentiment_service import MarketSentimentService
    
    try:
        data = await MarketSentimentService.get_market_sentiment()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fund-detail/{fund_code}")
async def get_fund_detail(fund_code: str):
    """获取基金详情（经理、规模、成立时间等）"""
    from services.fund_detail_service import FundDetailService
    
    try:
        data = await FundDetailService.get_fund_detail(fund_code)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news")
async def get_fund_news(fund_type: str = None, related_etf: str = None, max_news: int = 5):
    """获取基金相关新闻"""
    from services.news_service import NewsService
    
    try:
        news = await NewsService.get_fund_related_news(
            fund_type=fund_type,
            related_etf_name=related_etf,
            max_news=min(max_news, 10)
        )
        return {"data": news}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 提示词配置 API ====================

# 提示词变量说明（用于前端展示）
PROMPT_VARIABLES = {
    "fund_analysis": {
        "fund_name": "基金名称",
        "fund_code": "基金代码",
        "fund_type": "基金类型",
        "fund_detail": "基金详情（经理、规模、成立时间等）",
        "current_value": "当前净值",
        "change_5d": "近5日涨跌幅(%)",
        "change_20d": "近20日涨跌幅(%)",
        "ma5": "MA5均线值",
        "ma10": "MA10均线值",
        "ma20": "MA20均线值",
        "rsi": "RSI(14)指标值",
        "macd": "MACD指标值",
        "risk_metrics": "风险指标（最大回撤、波动率、夏普比率等）",
        "etf_info": "关联ETF行情信息",
        "holding_info": "当前持仓信息",
        "position_info": "账户仓位信息",
        "market_sentiment": "A股市场情绪数据",
        "related_news": "相关行业新闻",
    },
    "portfolio_analysis": {
        "account_summary": "账户整体汇总信息",
        "holdings_detail": "各基金持仓明细",
    }
}


@router.get("/prompts")
async def get_prompts_config():
    """获取提示词配置及变量说明"""
    prompts = load_prompts()
    
    return {
        "prompts": {
            "fund_analysis": {
                "system_prompt": prompts.get("fund_analysis", {}).get("system_prompt", ""),
                "user_prompt": prompts.get("fund_analysis", {}).get("user_prompt", ""),
            },
            "portfolio_analysis": {
                "system_prompt": prompts.get("portfolio_analysis", {}).get("system_prompt", ""),
                "user_prompt": prompts.get("portfolio_analysis", {}).get("user_prompt", ""),
            }
        },
        "variables": PROMPT_VARIABLES
    }


@router.post("/prompts")
async def update_prompts_config(data: PromptsUpdate):
    """更新提示词配置"""
    try:
        # 读取现有配置
        prompts = load_prompts()
        
        # 更新基金分析提示词
        if "fund_analysis" not in prompts:
            prompts["fund_analysis"] = {}
        if data.fund_analysis_system is not None:
            prompts["fund_analysis"]["system_prompt"] = data.fund_analysis_system
        if data.fund_analysis_user is not None:
            prompts["fund_analysis"]["user_prompt"] = data.fund_analysis_user
        
        # 更新持仓分析提示词
        if "portfolio_analysis" not in prompts:
            prompts["portfolio_analysis"] = {}
        if data.portfolio_analysis_system is not None:
            prompts["portfolio_analysis"]["system_prompt"] = data.portfolio_analysis_system
        if data.portfolio_analysis_user is not None:
            prompts["portfolio_analysis"]["user_prompt"] = data.portfolio_analysis_user
        
        # 保存到文件
        with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
        
        return {"message": "提示词配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.post("/prompts/reset")
async def reset_prompts_config():
    """重置提示词为默认配置"""
    try:
        default_prompts = {
            "fund_analysis": {
                "system_prompt": "你是专业的基金投资顾问，擅长技术分析、量化分析和风险管理。你的分析需要综合考虑技术面、基本面、市场情绪和风险控制等多个维度。",
                "user_prompt": """你是一位专业的基金投资顾问。请根据以下多维度数据分析该基金的投资建议。

## 基金基本信息
- 基金名称: {fund_name}
- 基金代码: {fund_code}
- 基金类型: {fund_type}

## 基金详情
{fund_detail}

## 技术指标数据（历史净值，近6个月）
- 当前净值: {current_value}
- 近5日涨跌幅: {change_5d}%
- 近20日涨跌幅: {change_20d}%
- MA5: {ma5}
- MA10: {ma10}
- MA20: {ma20}
- RSI(14): {rsi}
- MACD: {macd}

## 风险指标分析（近6个月）
{risk_metrics}

## 关联 ETF 当日行情
{etf_info}

## A股市场情绪
{market_sentiment}

## 相关行业新闻
{related_news}

## 持仓信息（如有）
{holding_info}

## 账户仓位信息
{position_info}

## 请回答
1. 当前技术面分析（趋势判断、均线支撑压力、RSI超买超卖信号）
2. 风险评估（最大回撤、波动率、夏普比率分析，判断风险收益性价比）
3. ETF 当日行情分析（如有关联 ETF，结合资金流向分析当日市场情绪）
4. 大盘环境分析（涨跌家数比、北向资金流向，判断整体市场氛围）
5. 行业新闻分析（结合相关新闻判断行业趋势和利好利空因素）
6. 买卖建议（强烈买入/买入/持有/卖出/强烈卖出）
7. 建议理由（分点说明，简洁明了，需结合技术面、基本面、市场情绪和新闻综合分析）
8. 风险提示（提示可能的风险点）
9. 仓位建议（注意：账户仓位比例是整个投资组合的总仓位，请综合考虑该基金在组合中的占比、当前市场环境给出建议）

注意：
- ETF 实时数据可以帮助你在收盘前（15:00前）做出更准确的判断。如果是交易时间，请重点参考 ETF 当日走势；非交易时间请参考历史数据。
- 市场情绪指标（涨跌家数比、北向资金）是重要的参考因素，当市场情绪极端时需要谨慎操作。
- 风险指标（最大回撤、波动率、夏普比率）帮助评估该基金的历史风险收益特征。
- 行业新闻可能包含重要的利好或利空消息，请重点关注政策变化、行业动态等。

请用简洁专业的语言回答，不要过于冗长。回复格式使用 Markdown。"""
            },
            "portfolio_analysis": {
                "system_prompt": "你是专业的基金投资顾问，擅长投资组合分析和资产配置。",
                "user_prompt": """你是一位专业的基金投资顾问。请根据以下数据对整个持仓组合进行综合分析。

## 账户整体情况
{account_summary}

## 持仓明细
{holdings_detail}

## 请回答
1. 组合整体分析（仓位是否合理、风险分散程度、资产配置建议）
2. 各基金点评（针对每只基金的简要评价和建议）
3. 调仓建议（是否需要调整各基金的配置比例）
4. 操作策略（近期市场环境下的具体操作建议）
5. 风险提示

请用简洁专业的语言回答，不要过于冗长。回复格式使用 Markdown。"""
            }
        }
        
        with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_prompts, f, ensure_ascii=False, indent=2)
        
        return {"message": "提示词已重置为默认配置", "prompts": default_prompts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")


# ==================== 数据库配置 API ====================

@router.get("/database-config")
async def get_database_config():
    """获取当前数据库配置"""
    import os
    
    db_type = os.getenv("DB_TYPE", "postgresql")
    
    # 判断当前使用的数据库类型
    is_sqlite = db_type.lower() == "sqlite"
    
    config = {
        "type": "sqlite" if is_sqlite else "postgresql",
        "sqlite": {
            "path": os.getenv("SQLITE_PATH", "data/funds.db"),
        },
        "postgresql": {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "name": os.getenv("DB_NAME", "funds"),
            "user": os.getenv("DB_USER", "postgres"),
            # 不返回密码
        }
    }
    
    return config


class DatabaseConfigUpdate(BaseModel):
    db_type: str  # "sqlite" or "postgresql"
    sqlite_path: Optional[str] = None
    pg_host: Optional[str] = None
    pg_port: Optional[str] = None
    pg_name: Optional[str] = None
    pg_user: Optional[str] = None
    pg_password: Optional[str] = None


@router.post("/database-config")
async def update_database_config(config: DatabaseConfigUpdate):
    """更新数据库配置（需要重启应用生效）"""
    import os
    from pathlib import Path
    
    try:
        env_file = Path(__file__).parent.parent / ".env"
        
        # 读取现有 .env
        env_vars = {}
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        env_vars[key.strip()] = value.strip()
        
        # 更新数据库类型（同时更新 env_vars 和 os.environ）
        db_type = config.db_type.lower()
        env_vars["DB_TYPE"] = db_type
        os.environ["DB_TYPE"] = db_type
        
        if db_type == "sqlite":
            if config.sqlite_path:
                env_vars["SQLITE_PATH"] = config.sqlite_path
                os.environ["SQLITE_PATH"] = config.sqlite_path
            # 清除 PostgreSQL 配置
            for key in ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]:
                env_vars.pop(key, None)
                os.environ.pop(key, None)
        else:
            if config.pg_host:
                env_vars["DB_HOST"] = config.pg_host
                os.environ["DB_HOST"] = config.pg_host
            if config.pg_port:
                env_vars["DB_PORT"] = config.pg_port
                os.environ["DB_PORT"] = config.pg_port
            if config.pg_name:
                env_vars["DB_NAME"] = config.pg_name
                os.environ["DB_NAME"] = config.pg_name
            if config.pg_user:
                env_vars["DB_USER"] = config.pg_user
                os.environ["DB_USER"] = config.pg_user
            # 只有当提供了新密码时才更新，否则保留原有密码
            if config.pg_password:
                env_vars["DB_PASSWORD"] = config.pg_password
                os.environ["DB_PASSWORD"] = config.pg_password
            # 清除 SQLite 配置
            env_vars.pop("SQLITE_PATH", None)
            os.environ.pop("SQLITE_PATH", None)
        
        # 写入 .env 文件
        lines = ["# 数据库配置", ""]
        lines.append(f"DB_TYPE={env_vars.get('DB_TYPE', 'postgresql')}")
        lines.append("")
        
        if env_vars.get("DB_TYPE", "postgresql").lower() == "sqlite":
            lines.append("# SQLite 配置")
            if "SQLITE_PATH" in env_vars:
                lines.append(f"SQLITE_PATH={env_vars['SQLITE_PATH']}")
        else:
            lines.append("# PostgreSQL 配置")
            for key in ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]:
                if key in env_vars:
                    lines.append(f"{key}={env_vars[key]}")
        
        lines.append("")
        lines.append("# DeepSeek API 配置")
        lines.append("")
        for key in ["DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"]:
            if key in env_vars:
                lines.append(f"{key}={env_vars[key]}")
        
        with open(env_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        return {
            "message": "数据库配置已保存，需要重启应用才能生效",
            "requires_restart": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


# ==================== 数据库测试和初始化 API ====================

class DatabaseTestRequest(BaseModel):
    db_type: str
    sqlite_path: Optional[str] = None
    pg_host: Optional[str] = None
    pg_port: Optional[str] = None
    pg_name: Optional[str] = None
    pg_user: Optional[str] = None
    pg_password: Optional[str] = None


@router.post("/database-test")
async def test_database_connection(request: DatabaseTestRequest):
    """测试数据库连接"""
    import sqlite3
    import psycopg2
    from pathlib import Path
    import os
    
    try:
        if request.db_type.lower() == "sqlite":
            # 测试 SQLite 连接
            db_path = request.sqlite_path or "data/funds.db"
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            
            return {
                "success": True,
                "message": "SQLite 连接成功",
                "database_type": "sqlite",
                "path": db_path
            }
        else:
            # 测试 PostgreSQL 连接
            # 如果前端传来的密码为空，使用当前环境变量中的密码
            password = request.pg_password if request.pg_password else os.getenv("DB_PASSWORD", "")
            
            conn = psycopg2.connect(
                host=request.pg_host or "localhost",
                port=request.pg_port or "5432",
                dbname=request.pg_name or "funds",
                user=request.pg_user or "postgres",
                password=password
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            
            return {
                "success": True,
                "message": "PostgreSQL 连接成功",
                "database_type": "postgresql"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"连接失败: {str(e)}",
            "database_type": request.db_type
        }


@router.post("/database-init")
async def initialize_database(request: DatabaseTestRequest):
    """初始化数据库表结构"""
    import sqlite3
    import psycopg2
    from pathlib import Path
    
    try:
        if request.db_type.lower() == "sqlite":
            # 初始化 SQLite
            db_path = request.sqlite_path or "data/funds.db"
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 创建表结构
            cursor.executescript("""
                -- 基金基础信息表
                CREATE TABLE IF NOT EXISTS funds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fund_code VARCHAR(6) UNIQUE NOT NULL,
                    fund_name VARCHAR(100) NOT NULL,
                    fund_type VARCHAR(50),
                    related_etf VARCHAR(20),
                    last_price_date DATE,
                    last_net_value REAL,
                    last_growth_rate REAL,
                    info_updated_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- 当前持仓表
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fund_code VARCHAR(6) NOT NULL,
                    total_shares REAL NOT NULL,
                    cost_price REAL NOT NULL,
                    total_cost REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
                );
                
                -- 交易记录表
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fund_code VARCHAR(6) NOT NULL,
                    trade_type VARCHAR(4) NOT NULL,
                    trade_date DATE NOT NULL,
                    confirm_date DATE,
                    confirm_shares REAL,
                    confirm_net_value REAL,
                    shares REAL,
                    price REAL,
                    amount REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
                );
                
                -- 历史净值缓存表
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fund_code VARCHAR(6) NOT NULL,
                    net_value REAL NOT NULL,
                    accum_value REAL,
                    date DATE NOT NULL,
                    growth_rate REAL,
                    UNIQUE(fund_code, date),
                    FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
                );
                
                -- 缓存元数据表
                CREATE TABLE IF NOT EXISTS cache_meta (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fund_code VARCHAR(6) NOT NULL UNIQUE,
                    last_sync_date DATE,
                    last_sync_time TIMESTAMP,
                    sync_status VARCHAR(20),
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
                );
                
                -- 设置表
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key VARCHAR(50) UNIQUE NOT NULL,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- AI 分析缓存表
                CREATE TABLE IF NOT EXISTS ai_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fund_code VARCHAR(20) NOT NULL,
                    analysis_type VARCHAR(20) NOT NULL DEFAULT 'fund',
                    analysis TEXT NOT NULL,
                    indicators TEXT,
                    risk_metrics TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(fund_code, analysis_type)
                );
                
                -- 创建索引
                CREATE INDEX IF NOT EXISTS idx_prices_fund_code ON prices(fund_code);
                CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);
                CREATE INDEX IF NOT EXISTS idx_trades_fund_code ON trades(fund_code);
                CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date);
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_fund_code ON ai_analysis(fund_code);
                
                -- 初始化默认设置
                INSERT OR IGNORE INTO settings (key, value) VALUES ('deepseek_api_key', '');
                INSERT OR IGNORE INTO settings (key, value) VALUES ('deepseek_base_url', 'https://api.deepseek.com/v1');
                INSERT OR IGNORE INTO settings (key, value) VALUES ('deepseek_model', 'deepseek-chat');
            """)
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": "SQLite 数据库初始化成功",
                "database_type": "sqlite",
                "path": db_path
            }
        else:
            # PostgreSQL 初始化使用原有的 init_db 逻辑
            from database import init_db

            # 临时修改连接参数
            import os
            original_host = os.environ.get("DB_HOST")
            original_port = os.environ.get("DB_PORT")
            original_name = os.environ.get("DB_NAME")
            original_user = os.environ.get("DB_USER")
            original_password = os.environ.get("DB_PASSWORD")
            
            os.environ["DB_HOST"] = request.pg_host or "localhost"
            os.environ["DB_PORT"] = request.pg_port or "5432"
            os.environ["DB_NAME"] = request.pg_name or "funds"
            os.environ["DB_USER"] = request.pg_user or "postgres"
            os.environ["DB_PASSWORD"] = request.pg_password or ""
            os.environ["DB_TYPE"] = "postgresql"
            
            try:
                init_db()
                return {
                    "success": True,
                    "message": "PostgreSQL 数据库初始化成功",
                    "database_type": "postgresql"
                }
            finally:
                # 恢复原始环境变量
                if original_host:
                    os.environ["DB_HOST"] = original_host
                if original_port:
                    os.environ["DB_PORT"] = original_port
                if original_name:
                    os.environ["DB_NAME"] = original_name
                if original_user:
                    os.environ["DB_USER"] = original_user
                if original_password:
                    os.environ["DB_PASSWORD"] = original_password
                    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")


@router.get("/database-status")
async def get_database_status():
    """获取当前数据库连接状态和表信息"""
    import os
    from pathlib import Path
    
    # 从环境变量读取配置
    db_type = os.getenv("DB_TYPE", "postgresql").lower()
    sqlite_path = os.getenv("SQLITE_PATH", "data/funds.db")
    
    try:
        # 尝试连接数据库
        from database import get_db
        conn = get_db()
        cursor = conn.cursor()
        
        # 获取表信息
        if db_type == "sqlite":
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            rows = cursor.fetchall()
            tables = [row[0] if isinstance(row, (list, tuple)) else row['name'] for row in rows]
            
            # 获取记录数
            table_counts = {}
            for table in tables:
                if table.startswith('sqlite_'):  # 跳过 SQLite 系统表
                    continue
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row = cursor.fetchone()
                count = row[0] if isinstance(row, (list, tuple)) else list(row.values())[0] if row else 0
                table_counts[table] = count
        else:
            # PostgreSQL - 查询 public schema 的表
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            rows = cursor.fetchall()
            tables = [row[0] if isinstance(row, (list, tuple)) else row['table_name'] for row in rows]
            
            # 获取记录数
            table_counts = {}
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    row = cursor.fetchone()
                    count = row[0] if isinstance(row, (list, tuple)) else list(row.values())[0] if row else 0
                    table_counts[table] = count
                except Exception as table_error:
                    table_counts[table] = -1  # 标记为无法读取
        
        conn.close()
        
        db_info = {
            "connected": True,
            "database_type": db_type,
            "tables": tables,
            "table_counts": table_counts,
            "total_tables": len(tables)
        }

        if db_type == "sqlite":
            db_info["path"] = sqlite_path
            db_info["file_exists"] = Path(sqlite_path).exists()
        
        return db_info
        
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Database status check failed: {error_detail}")  # 打印到服务器日志
        return {
            "connected": False,
            "database_type": db_type,
            "error": str(e)
        }
