"""基金管理路由"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List

from services.fund_service import FundService
from services.market_service import MarketService

router = APIRouter(prefix="/api/funds", tags=["基金管理"])


class FundCreate(BaseModel):
    fund_code: str
    fund_name: Optional[str] = None
    fund_type: Optional[str] = None
    risk_level: Optional[str] = None


class FundUpdate(BaseModel):
    fund_name: Optional[str] = None
    fund_type: Optional[str] = None
    risk_level: Optional[str] = None


@router.get("")
async def get_funds():
    """获取所有基金列表"""
    funds = FundService.get_all_funds()
    return {"data": funds}


@router.get("/{fund_code}")
async def get_fund(fund_code: str):
    """获取单个基金信息"""
    fund = FundService.get_fund_by_code(fund_code)
    if not fund:
        raise HTTPException(status_code=404, detail="基金不存在")
    return fund


@router.post("")
async def add_fund(fund: FundCreate):
    """添加基金"""
    try:
        # 如果没有提供基金名称，尝试从 AkShare 获取
        if not fund.fund_name:
            info = await MarketService.fetch_fund_info_from_akshare(fund.fund_code)
            if info:
                fund.fund_name = info.get("fund_name")
                if not fund.fund_type:
                    fund.fund_type = info.get("fund_type")
        
        if not fund.fund_name:
            raise HTTPException(status_code=400, detail="无法获取基金信息，请手动输入基金名称")
        
        result = FundService.add_fund(
            fund.fund_code,
            fund.fund_name,
            fund.fund_type,
            fund.risk_level
        )
        
        # 后台同步历史数据
        import asyncio
        asyncio.create_task(MarketService.sync_fund_history(fund.fund_code))
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{fund_code}")
async def update_fund(fund_code: str, fund: FundUpdate):
    """更新基金信息"""
    result = FundService.update_fund(
        fund_code,
        **{k: v for k, v in fund.model_dump().items() if v is not None}
    )
    if not result:
        raise HTTPException(status_code=404, detail="基金不存在")
    return result


@router.delete("/{fund_code}")
async def delete_fund(fund_code: str):
    """删除基金"""
    success = FundService.delete_fund(fund_code)
    if not success:
        raise HTTPException(status_code=404, detail="基金不存在")
    return {"message": "删除成功"}


@router.get("/search/{keyword}")
async def search_funds(keyword: str, limit: int = Query(default=20, le=50)):
    """搜索基金"""
    results = await MarketService.search_funds(keyword, limit)
    return {"data": results}
