from .funds import router as funds_router
from .holdings import router as holdings_router
from .trades import router as trades_router
from .market import router as market_router
from .ai import router as ai_router
from .etf import router as etf_router

__all__ = [
    "funds_router",
    "holdings_router",
    "trades_router",
    "market_router",
    "ai_router",
    "etf_router",
]
