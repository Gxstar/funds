"""数据模型定义"""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Fund:
    """基金基础信息"""
    id: Optional[int] = None
    fund_code: str = ""
    fund_name: str = ""
    fund_type: Optional[str] = None
    risk_level: Optional[str] = None
    related_etf: Optional[str] = None
    last_price_date: Optional[date] = None
    last_net_value: Optional[Decimal] = None
    last_growth_rate: Optional[Decimal] = None
    info_updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row: dict) -> "Fund":
        return cls(
            id=row.get("id"),
            fund_code=row.get("fund_code", ""),
            fund_name=row.get("fund_name", ""),
            fund_type=row.get("fund_type"),
            risk_level=row.get("risk_level"),
            related_etf=row.get("related_etf"),
            last_price_date=row.get("last_price_date"),
            last_net_value=Decimal(str(row["last_net_value"])) if row.get("last_net_value") else None,
            last_growth_rate=Decimal(str(row["last_growth_rate"])) if row.get("last_growth_rate") else None,
            info_updated_at=row.get("info_updated_at"),
            created_at=row.get("created_at"),
        )


@dataclass
class Holding:
    """当前持仓"""
    id: Optional[int] = None
    fund_code: str = ""
    total_shares: Decimal = Decimal("0")
    cost_price: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row: dict) -> "Holding":
        return cls(
            id=row.get("id"),
            fund_code=row.get("fund_code", ""),
            total_shares=Decimal(str(row.get("total_shares", 0))),
            cost_price=Decimal(str(row.get("cost_price", 0))),
            total_cost=Decimal(str(row.get("total_cost", 0))),
            updated_at=row.get("updated_at"),
        )


@dataclass
class Trade:
    """交易记录"""
    id: Optional[int] = None
    fund_code: str = ""
    trade_type: str = ""  # BUY / SELL
    trade_date: date = None
    confirm_date: Optional[date] = None
    confirm_shares: Optional[Decimal] = None
    confirm_net_value: Optional[Decimal] = None
    shares: Optional[Decimal] = None
    price: Optional[Decimal] = None
    amount: Decimal = Decimal("0")
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row: dict) -> "Trade":
        return cls(
            id=row.get("id"),
            fund_code=row.get("fund_code", ""),
            trade_type=row.get("trade_type", ""),
            trade_date=row.get("trade_date"),
            confirm_date=row.get("confirm_date"),
            confirm_shares=Decimal(str(row["confirm_shares"])) if row.get("confirm_shares") else None,
            confirm_net_value=Decimal(str(row["confirm_net_value"])) if row.get("confirm_net_value") else None,
            shares=Decimal(str(row["shares"])) if row.get("shares") else None,
            price=Decimal(str(row["price"])) if row.get("price") else None,
            amount=Decimal(str(row.get("amount", 0))),
            created_at=row.get("created_at"),
        )


@dataclass
class Price:
    """历史净值"""
    id: Optional[int] = None
    fund_code: str = ""
    net_value: Decimal = Decimal("0")
    accum_value: Optional[Decimal] = None
    date: date = None
    growth_rate: Optional[Decimal] = None
    
    @classmethod
    def from_row(cls, row: dict) -> "Price":
        return cls(
            id=row.get("id"),
            fund_code=row.get("fund_code", ""),
            net_value=Decimal(str(row.get("net_value", 0))),
            accum_value=Decimal(str(row["accum_value"])) if row.get("accum_value") else None,
            date=row.get("date"),
            growth_rate=Decimal(str(row["growth_rate"])) if row.get("growth_rate") else None,
        )


@dataclass
class CacheMeta:
    """缓存元数据"""
    id: Optional[int] = None
    fund_code: str = ""
    last_sync_date: Optional[date] = None
    last_sync_time: Optional[datetime] = None
    sync_status: str = ""  # synced / pending / failed
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row: dict) -> "CacheMeta":
        return cls(
            id=row.get("id"),
            fund_code=row.get("fund_code", ""),
            last_sync_date=row.get("last_sync_date"),
            last_sync_time=row.get("last_sync_time"),
            sync_status=row.get("sync_status", ""),
            error_message=row.get("error_message"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )


@dataclass
class Setting:
    """系统设置"""
    id: Optional[int] = None
    key: str = ""
    value: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row: dict) -> "Setting":
        return cls(
            id=row.get("id"),
            key=row.get("key", ""),
            value=row.get("value"),
            updated_at=row.get("updated_at"),
        )


@dataclass
class AIAnalysis:
    """AI 分析缓存"""
    id: Optional[int] = None
    fund_code: str = ""
    analysis_type: str = "fund"  # fund / portfolio
    analysis: str = ""
    indicators: Optional[dict] = None
    risk_metrics: Optional[dict] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row: dict) -> "AIAnalysis":
        return cls(
            id=row.get("id"),
            fund_code=row.get("fund_code", ""),
            analysis_type=row.get("analysis_type", "fund"),
            analysis=row.get("analysis", ""),
            indicators=row.get("indicators"),
            risk_metrics=row.get("risk_metrics"),
            created_at=row.get("created_at"),
        )
