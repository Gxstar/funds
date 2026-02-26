"""ETF 行情路由"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from services.etf_service import ETFService
from services.fund_service import FundService

router = APIRouter(prefix="/api/etf", tags=["ETF 行情"])


@router.get("/realtime/{etf_code}")
async def get_etf_realtime(etf_code: str):
    """获取 ETF 实时行情"""
    result = await ETFService.get_etf_realtime(etf_code)
    if not result:
        raise HTTPException(status_code=404, detail="未找到该 ETF 或获取数据失败")
    return result


@router.get("/money-flow/{etf_code}")
async def get_etf_money_flow(etf_code: str):
    """获取 ETF 资金流向"""
    result = await ETFService.get_etf_money_flow(etf_code)
    if not result:
        raise HTTPException(status_code=404, detail="未找到该 ETF 或获取数据失败")
    return result


@router.get("/analysis/{etf_code}")
async def get_etf_analysis(etf_code: str):
    """获取 ETF 完整分析数据（实时行情 + 资金流向）"""
    result = await ETFService.get_etf_analysis_data(etf_code)
    return result


@router.get("/recommend/{fund_type}")
async def get_recommended_etfs(fund_type: str):
    """根据基金类型推荐关联 ETF"""
    etfs = ETFService.get_recommended_etfs(fund_type)
    return {"fund_type": fund_type, "recommended_etfs": etfs}


@router.get("/fund/{fund_code}")
async def get_fund_etf_data(fund_code: str):
    """获取基金关联 ETF 的分析数据"""
    fund = FundService.get_fund_by_code(fund_code)
    if not fund:
        raise HTTPException(status_code=404, detail="基金不存在")
    
    related_etf = fund.get("related_etf")
    if not related_etf:
        # 尝试推荐
        fund_type = fund.get("fund_type", "")
        recommended = ETFService.get_recommended_etfs(fund_type)
        return {
            "has_related_etf": False,
            "fund_code": fund_code,
            "fund_name": fund.get("fund_name"),
            "fund_type": fund_type,
            "recommended_etfs": recommended,
            "etf_data": None
        }
    
    # 获取关联 ETF 数据
    etf_data = await ETFService.get_etf_analysis_data(related_etf)
    
    return {
        "has_related_etf": True,
        "fund_code": fund_code,
        "fund_name": fund.get("fund_name"),
        "fund_type": fund.get("fund_type"),
        "related_etf": related_etf,
        "etf_data": etf_data
    }
