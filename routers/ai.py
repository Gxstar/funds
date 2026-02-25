"""AI 建议路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional

from services.ai_service import AIService

router = APIRouter(prefix="/api/ai", tags=["AI建议"])


class SettingsUpdate(BaseModel):
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: Optional[str] = None
    deepseek_model: Optional[str] = None


class PositionSettingUpdate(BaseModel):
    total_position_amount: Optional[str] = None  # 满仓金额，可选


@router.get("/status")
async def get_ai_status():
    """获取 AI 配置状态"""
    return {
        "configured": AIService.is_configured()
    }


@router.post("/suggest/{fund_code}")
async def suggest_fund(fund_code: str):
    """获取单只基金建议"""
    result = await AIService.analyze_fund(fund_code)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/analyze")
async def analyze_portfolio():
    """分析持仓组合"""
    result = await AIService.analyze_portfolio()
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


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
