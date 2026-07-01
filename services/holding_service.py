"""持仓管理服务"""
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from collections import defaultdict

from database.connection import get_db_context

logger = logging.getLogger(__name__)


class HoldingService:
    """持仓管理服务"""

    @staticmethod
    def get_holding(fund_code: str) -> Optional[dict]:
        """获取单只基金持仓"""
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT h.*, f.fund_name, f.last_net_value, f.last_growth_rate
                FROM holdings h
                JOIN funds f ON h.fund_code = f.fund_code
                WHERE h.fund_code = %s
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
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM holdings WHERE fund_code = %s", (fund_code,)
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE holdings 
                    SET total_shares = %s, cost_price = %s, total_cost = %s, updated_at = %s
                    WHERE fund_code = %s
                """, (float(total_shares), float(cost_price), float(total_cost), datetime.now(), fund_code))
            else:
                cursor.execute("""
                    INSERT INTO holdings (fund_code, total_shares, cost_price, total_cost)
                    VALUES (%s, %s, %s, %s)
                """, (fund_code, float(total_shares), float(cost_price), float(total_cost)))

            cursor.execute("""
                SELECT h.*, f.fund_name, f.last_net_value, f.last_growth_rate
                FROM holdings h
                JOIN funds f ON h.fund_code = f.fund_code
                WHERE h.fund_code = %s
            """, (fund_code,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def delete_holding(fund_code: str) -> bool:
        """删除持仓"""
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM holdings WHERE fund_code = %s", (fund_code,)
            )
            return cursor.rowcount > 0

    @staticmethod
    def get_holdings_summary() -> dict:
        """获取持仓汇总"""
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(h.total_cost), 0) as total_cost,
                    COUNT(h.fund_code) as fund_count
                FROM holdings h
            """)
            summary_row = cursor.fetchone()

            total_cost = Decimal(str(summary_row["total_cost"] or 0))
            fund_count = summary_row["fund_count"]

            cursor.execute("""
                SELECT h.fund_code, h.total_shares, h.total_cost, 
                       f.last_net_value, f.last_growth_rate, f.last_price_date
                FROM holdings h
                LEFT JOIN funds f ON h.fund_code = f.fund_code
            """)

            total_market_value = Decimal("0")
            today_profit = Decimal("0")

            for row in cursor.fetchall():
                shares = Decimal(str(row["total_shares"])) if row["total_shares"] else Decimal("0")
                net_value = Decimal(str(row["last_net_value"])) if row["last_net_value"] else Decimal("0")
                growth_rate = Decimal(str(row["last_growth_rate"])) if row["last_growth_rate"] else Decimal("0")

                market_value = shares * net_value
                total_market_value += market_value

                today_profit += market_value * growth_rate / 100

            total_profit = total_market_value - total_cost
            profit_rate = (total_profit / total_cost * 100) if total_cost else Decimal("0")

            return {
                "total_cost": total_cost,
                "total_market_value": total_market_value,
                "total_profit": total_profit,
                "profit_rate": profit_rate,
                "today_profit": today_profit,
                "fund_count": fund_count
            }

    @staticmethod
    def _upsert_holding_in_transaction(cursor, fund_code, total_shares, cost_price, total_cost, is_sqlite):
        """在已有事务中更新持仓（不单独提交）"""
        placeholder = "?" if is_sqlite else "%s"
        now_expr = "datetime('now')" if is_sqlite else "NOW()"
        cursor.execute(
            f"""UPDATE holdings SET total_shares = {placeholder}, cost_price = {placeholder},
                total_cost = {placeholder}, updated_at = {now_expr}
                WHERE fund_code = {placeholder}""",
            (total_shares, cost_price, total_cost, fund_code,)
        )

    @staticmethod
    def recalculate_holding(fund_code: str) -> Optional[dict]:
        """根据交易记录重新计算持仓"""
        from database.connection import DB_TYPE
        is_sqlite = DB_TYPE == "sqlite"

        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT trade_type, confirm_shares, confirm_net_value, amount
                FROM trades
                WHERE fund_code = %s
                ORDER BY trade_date, created_at
            """, (fund_code,))

            trades = cursor.fetchall()

            if not trades:
                cursor.execute("DELETE FROM holdings WHERE fund_code = %s", (fund_code,))
                return None

            total_shares = Decimal("0")
            total_cost = Decimal("0")

            for trade in trades:
                shares = Decimal(str(trade["confirm_shares"] or 0))
                amount = Decimal(str(trade["amount"] or 0))

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
                HoldingService._upsert_holding_in_transaction(
                    cursor, fund_code, float(total_shares), float(cost_price), float(total_cost), is_sqlite
                )

                cursor.execute("""
                    SELECT h.*, f.fund_name, f.last_net_value, f.last_growth_rate
                    FROM holdings h
                    JOIN funds f ON h.fund_code = f.fund_code
                    WHERE h.fund_code = %s
                """, (fund_code,))
                row = cursor.fetchone()
                return dict(row) if row else None
            else:
                cursor.execute("DELETE FROM holdings WHERE fund_code = %s", (fund_code,))
                return None

    @staticmethod
    def get_portfolio_history(days: int = 90) -> dict:
        """获取持仓组合历史收益数据"""
        from datetime import timedelta

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        with get_db_context() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT h.fund_code, h.total_shares, h.total_cost, f.fund_name
                FROM holdings h
                JOIN funds f ON h.fund_code = f.fund_code
            """)
            holdings = {row["fund_code"]: dict(row) for row in cursor.fetchall()}

            if not holdings:
                return {"dates": [], "market_values": [], "costs": [], "profits": [], "profit_rates": []}

            fund_codes = list(holdings.keys())
            placeholders = ",".join(["%s"] * len(fund_codes))

            cursor.execute(f"""
                SELECT fund_code, date, net_value
                FROM prices
                WHERE fund_code IN ({placeholders})
                AND date >= %s AND date <= %s
                ORDER BY date ASC
            """, fund_codes + [start_date, end_date])

            prices = cursor.fetchall()

            daily_prices = defaultdict(dict)
            for p in prices:
                daily_prices[p["date"]][p["fund_code"]] = float(p["net_value"] or 0)

            cursor.execute(f"""
                SELECT fund_code, trade_date, trade_type, amount, confirm_shares
                FROM trades
                WHERE fund_code IN ({placeholders})
                AND trade_date <= %s
                ORDER BY trade_date ASC
            """, fund_codes + [end_date])

            trades = cursor.fetchall()

            fund_trades = defaultdict(list)
            for t in trades:
                fund_trades[t["fund_code"]].append({
                    "date": t["trade_date"],
                    "type": t["trade_type"],
                    "amount": float(t["amount"] or 0),
                    "shares": float(t["confirm_shares"] or 0)
                })

            dates = sorted(daily_prices.keys())
            market_values = []
            costs = []
            profits = []
            profit_rates = []

            for d in dates:
                daily_market_value = 0
                daily_cost = 0

                for code, holding in holdings.items():
                    if code in daily_prices[d]:
                        shares = HoldingService._calculate_shares_on_date(
                            code, d, float(holding["total_shares"]), fund_trades[code]
                        )

                        value = shares * daily_prices[d][code]
                        daily_market_value += value

                        cost = HoldingService._calculate_cost_on_date(
                            code, d, float(holding["total_cost"]), fund_trades[code]
                        )
                        daily_cost += cost

                market_values.append(round(daily_market_value, 2))
                costs.append(round(daily_cost, 2))
                profit = daily_market_value - daily_cost
                profits.append(round(profit, 2))
                profit_rate = (profit / daily_cost * 100) if daily_cost > 0 else 0
                profit_rates.append(round(profit_rate, 2))

            return {
                "dates": dates,
                "market_values": market_values,
                "costs": costs,
                "profits": profits,
                "profit_rates": profit_rates
            }

    @staticmethod
    def _calculate_shares_on_date(fund_code: str, target_date: date, current_shares: float, trades: list) -> float:
        """计算某日期之前的持仓份额（逆向推算）"""
        shares = current_shares

        for trade in reversed(trades):
            if trade["date"] > target_date:
                if trade["type"] == "BUY":
                    shares -= trade["shares"]
                else:
                    shares += trade["shares"]

        return max(0, shares)

    @staticmethod
    def _calculate_cost_on_date(fund_code: str, target_date: date, current_cost: float, trades: list) -> float:
        """计算某日期之前的投入成本（逆向推算）"""
        cost = current_cost

        for trade in reversed(trades):
            if trade["date"] > target_date:
                if trade["type"] == "BUY":
                    cost -= trade["amount"]
                else:
                    cost += trade["amount"]

        return max(0, cost)
