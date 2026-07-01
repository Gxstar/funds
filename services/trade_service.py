"""交易记录服务"""
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from database.connection import get_db_context

logger = logging.getLogger(__name__)


class TradeService:
    """交易记录服务"""

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
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (fund_code, trade_type, trade_date, confirm_date, confirm_shares, confirm_net_value, amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (fund_code, trade_type, trade_date, confirm_date, 
                  float(confirm_shares) if confirm_shares else None,
                  float(confirm_net_value) if confirm_net_value else None,
                  float(amount)))

            trade_id = cursor.fetchone()["id"]

            actual_shares = confirm_shares
            if not actual_shares and confirm_net_value and amount:
                actual_shares = amount / confirm_net_value

            if actual_shares:
                cursor.execute(
                    "SELECT id, total_shares, total_cost FROM holdings WHERE fund_code = %s", (fund_code,)
                )
                existing = cursor.fetchone()

                if trade_type == "BUY":
                    if existing:
                        current_shares = Decimal(str(existing["total_shares"]))
                        current_cost = Decimal(str(existing["total_cost"]))
                        new_shares = current_shares + actual_shares
                        new_cost = current_cost + amount
                        new_cost_price = new_cost / new_shares if new_shares else Decimal("0")
                        cursor.execute("""
                            UPDATE holdings 
                            SET total_shares = %s, cost_price = %s, total_cost = %s, updated_at = %s
                            WHERE fund_code = %s
                        """, (float(new_shares), float(new_cost_price), float(new_cost), datetime.now(), fund_code))
                    else:
                        cost_price = confirm_net_value if confirm_net_value else (amount / actual_shares if actual_shares else Decimal("0"))
                        cursor.execute("""
                            INSERT INTO holdings (fund_code, total_shares, cost_price, total_cost)
                            VALUES (%s, %s, %s, %s)
                        """, (fund_code, float(actual_shares), float(cost_price), float(amount)))
                elif trade_type == "SELL":
                    if not existing:
                        cursor.execute("DELETE FROM trades WHERE id = %s", (trade_id,))
                        raise ValueError(f"无法卖出：当前未持有该基金")

                    current_shares = Decimal(str(existing["total_shares"]))
                    if current_shares < actual_shares:
                        cursor.execute("DELETE FROM trades WHERE id = %s", (trade_id,))
                        raise ValueError(f"份额不足：当前持有 {current_shares:.2f} 份，尝试卖出 {actual_shares:.2f} 份")

                    current_cost = Decimal(str(existing["total_cost"]))
                    cost_per_share = current_cost / current_shares
                    new_shares = current_shares - actual_shares
                    new_cost = current_cost - (cost_per_share * actual_shares)
                    if new_shares > 0:
                        new_cost_price = new_cost / new_shares
                        cursor.execute("""
                            UPDATE holdings 
                            SET total_shares = %s, cost_price = %s, total_cost = %s, updated_at = %s
                            WHERE fund_code = %s
                        """, (float(new_shares), float(new_cost_price), float(new_cost), datetime.now(), fund_code))
                    else:
                        cursor.execute("DELETE FROM holdings WHERE fund_code = %s", (fund_code,))

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
            cursor = conn.cursor()
            if fund_code:
                cursor.execute("""
                    SELECT t.*, f.fund_name
                    FROM trades t
                    JOIN funds f ON t.fund_code = f.fund_code
                    WHERE t.fund_code = %s
                    ORDER BY t.trade_date DESC, t.created_at DESC
                    LIMIT %s OFFSET %s
                """, (fund_code, limit, offset))
            else:
                cursor.execute("""
                    SELECT t.*, f.fund_name
                    FROM trades t
                    JOIN funds f ON t.fund_code = f.fund_code
                    ORDER BY t.trade_date DESC, t.created_at DESC
                    LIMIT %s OFFSET %s
                """, (limit, offset))

            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def update_trade(
        trade_id: int,
        trade_type: Optional[str] = None,
        trade_date: Optional[date] = None,
        confirm_date: Optional[date] = None,
        confirm_shares: Optional[Decimal] = None,
        confirm_net_value: Optional[Decimal] = None,
        amount: Optional[Decimal] = None
    ) -> Optional[dict]:
        """更新交易记录"""
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM trades WHERE id = %s", (trade_id,)
            )
            existing = cursor.fetchone()
            if not existing:
                return None

            fund_code = existing["fund_code"]

            updates = {}
            if trade_type:
                updates["trade_type"] = trade_type
            if trade_date:
                updates["trade_date"] = trade_date
            if confirm_date is not None:
                updates["confirm_date"] = confirm_date
            if confirm_shares is not None:
                updates["confirm_shares"] = float(confirm_shares)
            if confirm_net_value is not None:
                updates["confirm_net_value"] = float(confirm_net_value)
            if amount is not None:
                updates["amount"] = float(amount)

            if updates:
                set_clause = ", ".join(f"{k} = %s" for k in updates.keys())
                values = list(updates.values()) + [trade_id]
                cursor.execute(f"UPDATE trades SET {set_clause} WHERE id = %s", values)

            cursor.execute(
                "SELECT * FROM trades WHERE id = %s", (trade_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def delete_trade(trade_id: int) -> bool:
        """删除交易记录"""
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM trades WHERE id = %s", (trade_id,)
            )
            return cursor.rowcount > 0
