"""基金业务服务"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
import logging

from database.connection import get_db_context
from database.models import Fund, Holding, Trade

logger = logging.getLogger(__name__)


class FundService:
    """基金管理服务"""
    
    @staticmethod
    def get_all_funds() -> List[dict]:
        """获取所有基金列表"""
        with get_db_context() as conn:
            cursor = conn.execute("""
                SELECT f.*, 
                       h.total_shares, h.cost_price, h.total_cost
                FROM funds f
                LEFT JOIN holdings h ON f.fund_code = h.fund_code
                ORDER BY f.created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_fund_by_code(fund_code: str) -> Optional[dict]:
        """根据代码获取基金"""
        with get_db_context() as conn:
            cursor = conn.execute("""
                SELECT f.*, 
                       h.total_shares, h.cost_price, h.total_cost
                FROM funds f
                LEFT JOIN holdings h ON f.fund_code = h.fund_code
                WHERE f.fund_code = ?
            """, (fund_code,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def add_fund(
        fund_code: str,
        fund_name: str,
        fund_type: Optional[str] = None,
        risk_level: Optional[str] = None
    ) -> dict:
        """添加基金"""
        with get_db_context() as conn:
            try:
                conn.execute("""
                    INSERT INTO funds (fund_code, fund_name, fund_type, risk_level)
                    VALUES (?, ?, ?, ?)
                """, (fund_code, fund_name, fund_type, risk_level))
                
                return {
                    "fund_code": fund_code,
                    "fund_name": fund_name,
                    "fund_type": fund_type,
                    "risk_level": risk_level
                }
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    raise ValueError(f"基金 {fund_code} 已存在")
                raise
    
    @staticmethod
    def update_fund(fund_code: str, **kwargs) -> Optional[dict]:
        """更新基金信息"""
        allowed_fields = ["fund_name", "fund_type", "risk_level", 
                         "last_price_date", "last_net_value", "last_growth_rate"]
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return None
        
        updates["info_updated_at"] = datetime.now()
        
        with get_db_context() as conn:
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [fund_code]
            
            conn.execute(f"""
                UPDATE funds SET {set_clause} WHERE fund_code = ?
            """, values)
            
            return FundService.get_fund_by_code(fund_code)
    
    @staticmethod
    def delete_fund(fund_code: str) -> bool:
        """删除基金（同时删除相关数据）"""
        with get_db_context() as conn:
            # 删除持仓
            conn.execute("DELETE FROM holdings WHERE fund_code = ?", (fund_code,))
            # 删除交易记录
            conn.execute("DELETE FROM trades WHERE fund_code = ?", (fund_code,))
            # 删除价格数据
            conn.execute("DELETE FROM prices WHERE fund_code = ?", (fund_code,))
            # 删除缓存元数据
            conn.execute("DELETE FROM cache_meta WHERE fund_code = ?", (fund_code,))
            # 删除基金
            cursor = conn.execute("DELETE FROM funds WHERE fund_code = ?", (fund_code,))
            return cursor.rowcount > 0
    
    @staticmethod
    def get_holdings_summary() -> dict:
        """获取持仓汇总"""
        with get_db_context() as conn:
            cursor = conn.execute("""
                SELECT 
                    COALESCE(SUM(h.total_cost), 0) as total_cost,
                    COUNT(h.fund_code) as fund_count
                FROM holdings h
            """)
            summary_row = cursor.fetchone()
            
            total_cost = Decimal(str(summary_row["total_cost"] or 0))
            fund_count = summary_row["fund_count"]
            
            # 计算当前市值（需要最新净值）
            cursor = conn.execute("""
                SELECT h.fund_code, h.total_shares, h.total_cost, f.last_net_value
                FROM holdings h
                LEFT JOIN funds f ON h.fund_code = f.fund_code
            """)
            
            total_market_value = Decimal("0")
            for row in cursor.fetchall():
                shares = Decimal(str(row["total_shares"]))
                net_value = Decimal(str(row["last_net_value"])) if row["last_net_value"] else Decimal("0")
                total_market_value += shares * net_value
            
            total_profit = total_market_value - total_cost
            profit_rate = (total_profit / total_cost * 100) if total_cost else Decimal("0")
            
            return {
                "total_cost": total_cost,
                "total_market_value": total_market_value,
                "total_profit": total_profit,
                "profit_rate": profit_rate,
                "fund_count": fund_count
            }
    
    @staticmethod
    def get_holding(fund_code: str) -> Optional[dict]:
        """获取单只基金持仓"""
        with get_db_context() as conn:
            cursor = conn.execute("""
                SELECT h.*, f.fund_name, f.last_net_value, f.last_growth_rate
                FROM holdings h
                JOIN funds f ON h.fund_code = f.fund_code
                WHERE h.fund_code = ?
            """, (fund_code,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def update_holding(
        fund_code: str,
        total_shares: Decimal,
        cost_price: Decimal,
        total_cost: Decimal
    ) -> Optional[dict]:
        """更新或创建持仓"""
        with get_db_context() as conn:
            # 检查是否已有持仓
            cursor = conn.execute(
                "SELECT id FROM holdings WHERE fund_code = ?", (fund_code,)
            )
            existing = cursor.fetchone()
            
            if existing:
                conn.execute("""
                    UPDATE holdings 
                    SET total_shares = ?, cost_price = ?, total_cost = ?, updated_at = ?
                    WHERE fund_code = ?
                """, (float(total_shares), float(cost_price), float(total_cost), datetime.now(), fund_code))
            else:
                conn.execute("""
                    INSERT INTO holdings (fund_code, total_shares, cost_price, total_cost)
                    VALUES (?, ?, ?, ?)
                """, (fund_code, float(total_shares), float(cost_price), float(total_cost)))
            
            # 在同一个连接中查询返回结果（避免事务未提交导致查不到数据）
            cursor = conn.execute("""
                SELECT h.*, f.fund_name, f.last_net_value, f.last_growth_rate
                FROM holdings h
                JOIN funds f ON h.fund_code = f.fund_code
                WHERE h.fund_code = ?
            """, (fund_code,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def delete_holding(fund_code: str) -> bool:
        """删除持仓"""
        with get_db_context() as conn:
            cursor = conn.execute(
                "DELETE FROM holdings WHERE fund_code = ?", (fund_code,)
            )
            return cursor.rowcount > 0
    
    @staticmethod
    def add_trade(
        fund_code: str,
        trade_type: str,
        trade_date: date,
        amount: Decimal,
        confirm_date: Optional[date] = None,
        confirm_shares: Optional[Decimal] = None,
        confirm_net_value: Optional[Decimal] = None
    ) -> dict:
        """添加交易记录"""
        with get_db_context() as conn:
            cursor = conn.execute("""
                INSERT INTO trades (fund_code, trade_type, trade_date, confirm_date, confirm_shares, confirm_net_value, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (fund_code, trade_type, trade_date, confirm_date, 
                  float(confirm_shares) if confirm_shares else None,
                  float(confirm_net_value) if confirm_net_value else None,
                  float(amount)))
            
            trade_id = cursor.lastrowid
            
            # 使用确认份额更新持仓（如果没有确认份额，则根据金额和确认净值计算）
            if trade_type == "BUY":
                actual_shares = confirm_shares
                if not actual_shares and confirm_net_value and amount:
                    actual_shares = amount / confirm_net_value
                
                if actual_shares:
                    holding = FundService.get_holding(fund_code)
                    if holding:
                        current_shares = Decimal(str(holding["total_shares"]))
                        current_cost = Decimal(str(holding["total_cost"]))
                        new_shares = current_shares + actual_shares
                        new_cost = current_cost + amount
                        new_cost_price = new_cost / new_shares if new_shares else Decimal("0")
                        FundService.update_holding(fund_code, new_shares, new_cost_price, new_cost)
                    else:
                        cost_price = confirm_net_value if confirm_net_value else (amount / actual_shares if actual_shares else Decimal("0"))
                        FundService.update_holding(fund_code, actual_shares, cost_price, amount)
            
            return {
                "id": trade_id,
                "fund_code": fund_code,
                "trade_type": trade_type,
                "trade_date": trade_date,
                "confirm_date": confirm_date,
                "confirm_shares": confirm_shares,
                "confirm_net_value": confirm_net_value,
                "amount": amount
            }
    
    @staticmethod
    def get_trades(
        fund_code: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[dict]:
        """获取交易记录"""
        with get_db_context() as conn:
            if fund_code:
                cursor = conn.execute("""
                    SELECT t.*, f.fund_name
                    FROM trades t
                    JOIN funds f ON t.fund_code = f.fund_code
                    WHERE t.fund_code = ?
                    ORDER BY t.trade_date DESC, t.created_at DESC
                    LIMIT ? OFFSET ?
                """, (fund_code, limit, offset))
            else:
                cursor = conn.execute("""
                    SELECT t.*, f.fund_name
                    FROM trades t
                    JOIN funds f ON t.fund_code = f.fund_code
                    ORDER BY t.trade_date DESC, t.created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def delete_trade(trade_id: int) -> bool:
        """删除交易记录"""
        with get_db_context() as conn:
            cursor = conn.execute(
                "DELETE FROM trades WHERE id = ?", (trade_id,)
            )
            return cursor.rowcount > 0
    
    @staticmethod
    def recalculate_holding(fund_code: str) -> Optional[dict]:
        """根据交易记录重新计算持仓"""
        with get_db_context() as conn:
            cursor = conn.execute("""
                SELECT trade_type, shares, price, amount
                FROM trades
                WHERE fund_code = ?
                ORDER BY trade_date, created_at
            """, (fund_code,))
            
            trades = cursor.fetchall()
            
            if not trades:
                FundService.delete_holding(fund_code)
                return None
            
            total_shares = Decimal("0")
            total_cost = Decimal("0")
            
            for trade in trades:
                shares = Decimal(str(trade["shares"]))
                amount = Decimal(str(trade["amount"]))
                
                if trade["trade_type"] == "BUY":
                    total_shares += shares
                    total_cost += amount
                else:
                    if total_shares > 0:
                        cost_per_share = total_cost / total_shares
                        total_shares -= shares
                        total_cost -= cost_per_share * shares
            
            if total_shares > 0:
                cost_price = total_cost / total_shares
                return FundService.update_holding(fund_code, total_shares, cost_price, total_cost)
            else:
                FundService.delete_holding(fund_code)
                return None
