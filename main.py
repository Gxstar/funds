"""FastAPI 应用入口"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from database.connection import init_db
from routers import (
    funds_router,
    holdings_router,
    trades_router,
    market_router,
    ai_router,
    etf_router
)
from services.sync_scheduler import scheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("初始化数据库...")
    init_db()
    
    logger.info("启动同步调度器...")
    await scheduler.start()
    
    # 启动时同步数据
    await scheduler.sync_on_startup()
    
    logger.info("应用启动完成")
    
    yield
    
    # 关闭时
    logger.info("停止同步调度器...")
    await scheduler.stop()
    logger.info("应用已关闭")


# 创建应用
app = FastAPI(
    title="基金投资管理工具",
    description="场外基金投资管理工具，支持持仓管理、行情查看、AI建议",
    version="1.0.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(funds_router)
app.include_router(holdings_router)
app.include_router(trades_router)
app.include_router(market_router)
app.include_router(ai_router)
app.include_router(etf_router)

# 静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    """主页面"""
    return FileResponse("templates/index.html")


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )