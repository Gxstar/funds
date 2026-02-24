"""持仓管理路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from decimal import Decimal

from services.fund_service import FundService

router = APIRouter(prefix="/api/holdings", tags=["持仓管理"])


class HoldingUpdate(BaseModel):
    total_shares: str
    cost_price: str
    total_cost: str


@router.get("")
async def get_holdings():
    """获取所有持仓"""
    funds = FundService.get_all_funds()
    # 只返回有持仓的基金
    holdings = [f for f in funds if f.get("total_shares")]
    summary = FundService.get_holdings_summary()
    
    return {
        "data": holdings,
        "summary": summary
    }


@router.get("/summary")
async def get_holdings_summary():
    """获取持仓汇总"""
    return FundService.get_holdings_summary()


@router.get("/{fund_code}")
async def get_holding(fund_code: str):
    """获取单只基金持仓"""
    holding = FundService.get_holding(fund_code)
    if not holding:
        raise HTTPException(status_code=404, detail="持仓不存在")
    return holding


@router.put("/{fund_code}")
async def update_holding(fund_code: str, holding: HoldingUpdate):
    """更新持仓信息"""
    result = FundService.update_holding(
        fund_code,
        Decimal(holding.total_shares),
        Decimal(holding.cost_price),
        Decimal(holding.total_cost)
    )
    if not result:
        raise HTTPException(status_code=404, detail="基金不存在")
    return result


@router.delete("/{fund_code}")
async def delete_holding(fund_code: str):
    """删除持仓"""
    success = FundService.delete_holding(fund_code)
    if not success:
        raise HTTPException(status_code=404, detail="持仓不存在")
    return {"message": "删除成功"}


@router.post("/{fund_code}/recalculate")
async def recalculate_holding(fund_code: str):
    """根据交易记录重新计算持仓"""
    result = FundService.recalculate_holding(fund_code)
    if result is None:
        return {"message": "持仓已清空"}
    return result
