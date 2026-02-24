"""交易记录路由"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from typing import Optional

from services.fund_service import FundService

router = APIRouter(prefix="/api/trades", tags=["交易记录"])


class TradeCreate(BaseModel):
    fund_code: str
    trade_type: str  # BUY / SELL
    trade_date: str  # YYYY-MM-DD 购买时间
    confirm_date: Optional[str] = None  # YYYY-MM-DD 确认时间
    confirm_shares: Optional[str] = None  # 确认份额
    confirm_net_value: Optional[str] = None  # 确认净值
    amount: str  # 金额


class TradeUpdate(BaseModel):
    trade_type: Optional[str] = None
    trade_date: Optional[str] = None
    confirm_date: Optional[str] = None
    confirm_shares: Optional[str] = None
    confirm_net_value: Optional[str] = None
    amount: Optional[str] = None


@router.get("")
async def get_trades(
    fund_code: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0)
):
    """获取交易记录"""
    trades = FundService.get_trades(fund_code, limit, offset)
    return {"data": trades}


@router.post("")
async def add_trade(trade: TradeCreate):
    """新增交易记录"""
    try:
        result = FundService.add_trade(
            fund_code=trade.fund_code,
            trade_type=trade.trade_type.upper(),
            trade_date=date.fromisoformat(trade.trade_date),
            confirm_date=date.fromisoformat(trade.confirm_date) if trade.confirm_date else None,
            confirm_shares=Decimal(trade.confirm_shares) if trade.confirm_shares else None,
            confirm_net_value=Decimal(trade.confirm_net_value) if trade.confirm_net_value else None,
            amount=Decimal(trade.amount)
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{trade_id}")
async def update_trade(trade_id: int, trade: TradeUpdate):
    """更新交易记录"""
    try:
        result = FundService.update_trade(
            trade_id=trade_id,
            trade_type=trade.trade_type.upper() if trade.trade_type else None,
            trade_date=date.fromisoformat(trade.trade_date) if trade.trade_date else None,
            confirm_date=date.fromisoformat(trade.confirm_date) if trade.confirm_date else None,
            confirm_shares=Decimal(trade.confirm_shares) if trade.confirm_shares else None,
            confirm_net_value=Decimal(trade.confirm_net_value) if trade.confirm_net_value else None,
            amount=Decimal(trade.amount) if trade.amount else None
        )
        if not result:
            raise HTTPException(status_code=404, detail="交易记录不存在")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{trade_id}")
async def delete_trade(trade_id: int):
    """删除交易记录"""
    success = FundService.delete_trade(trade_id)
    if not success:
        raise HTTPException(status_code=404, detail="交易记录不存在")
    return {"message": "删除成功"}


@router.post("/{fund_code}/recalculate")
async def recalculate_after_delete(fund_code: str):
    """删除交易后重新计算持仓"""
    result = FundService.recalculate_holding(fund_code)
    return result or {"message": "持仓已清空"}
