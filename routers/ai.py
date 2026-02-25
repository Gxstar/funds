"""AI 建议路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.ai_service import AIService

router = APIRouter(prefix="/api/ai", tags=["AI建议"])


class SettingsUpdate(BaseModel):
    deepseek_api_key: str = None
    deepseek_base_url: str = None
    deepseek_model: str = None


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
    from utils.helpers import get_setting
    api_key = get_setting("deepseek_api_key")
    return {
        "api_key_configured": bool(api_key),
        "deepseek_api_key": "***" if api_key else "",
        "deepseek_base_url": get_setting("deepseek_base_url") or "https://api.deepseek.com/v1",
        "deepseek_model": get_setting("deepseek_model") or "deepseek-chat"
    }


@router.post("/settings")
async def update_settings(settings: SettingsUpdate):
    """更新 AI 设置，保存到 .env 文件"""
    from utils.helpers import set_env_setting
    
    if settings.deepseek_api_key is not None:
        set_env_setting("deepseek_api_key", settings.deepseek_api_key or None)
    if settings.deepseek_base_url is not None:
        set_env_setting("deepseek_base_url", settings.deepseek_base_url or None)
    if settings.deepseek_model is not None:
        set_env_setting("deepseek_model", settings.deepseek_model or None)
    
    return {"message": "设置已保存到 .env 文件"}
