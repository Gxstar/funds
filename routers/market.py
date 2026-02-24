"""行情数据路由"""
from fastapi import APIRouter, Query
from typing import Optional

from services.market_service import MarketService

router = APIRouter(prefix="/api/market", tags=["行情数据"])


@router.get("/{fund_code}")
async def get_market_info(fund_code: str):
    """获取基金实时信息"""
    # 先从数据库获取
    from services.fund_service import FundService
    fund = FundService.get_fund_by_code(fund_code)
    
    if not fund:
        return {"error": "基金不存在"}
    
    # 获取缓存状态
    cache_meta = MarketService.get_cache_meta(fund_code)
    
    return {
        **fund,
        "cache_status": cache_meta
    }


@router.get("/{fund_code}/history")
async def get_history(
    fund_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """获取历史净值"""
    from datetime import date
    
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None
    
    prices = MarketService.get_prices_from_db(fund_code, start, end)
    cache_meta = MarketService.get_cache_meta(fund_code)
    
    return {
        "fund_code": fund_code,
        "data": prices,
        "cache": cache_meta
    }


@router.get("/{fund_code}/chart")
async def get_chart(
    fund_code: str,
    period: str = Query(default="1y", pattern="^(3m|6m|1y|3y|5y|all)$")
):
    """获取图表数据"""
    chart_data = MarketService.get_chart_data(fund_code, period)
    return chart_data


@router.post("/{fund_code}/sync")
async def sync_fund(fund_code: str, force: bool = False):
    """手动同步基金数据"""
    result = await MarketService.sync_fund_history(fund_code, force)
    return result


@router.post("/sync-all")
async def sync_all_funds():
    """同步所有基金数据"""
    from services.fund_service import FundService
    import asyncio
    
    funds = FundService.get_all_funds()
    results = []
    
    for fund in funds:
        result = await MarketService.sync_fund_history(fund["fund_code"])
        results.append(result)
        await asyncio.sleep(1.5)  # 限流
    
    return {"results": results}
