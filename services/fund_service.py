"""基金业务服务"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
import logging

from database.connection import get_db_context

logger = logging.getLogger(__name__)


class FundService:
    """基金管理服务"""
    
    @staticmethod
    def get_all_funds() -> List[dict]:
        """获取所有基金列表"""
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute("""
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
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.*, 
                       h.total_shares, h.cost_price, h.total_cost
                FROM funds f
                LEFT JOIN holdings h ON f.fund_code = h.fund_code
                WHERE f.fund_code = %s
            """, (fund_code,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def add_fund(
        fund_code: str,
        fund_name: str,
        fund_type: Optional[str] = None
    ) -> dict:
        """添加基金"""
        with get_db_context() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO funds (fund_code, fund_name, fund_type)
                    VALUES (%s, %s, %s)
                """, (fund_code, fund_name, fund_type))
                
                return {
                    "fund_code": fund_code,
                    "fund_name": fund_name,
                    "fund_type": fund_type
                }
            except Exception as e:
                if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                    raise ValueError(f"基金 {fund_code} 已存在")
                raise
    
    @staticmethod
    def update_fund(fund_code: str, **kwargs) -> Optional[dict]:
        """更新基金信息"""
        allowed_fields = ["fund_name", "fund_type", "related_etf", 
                         "last_price_date", "last_net_value", "last_growth_rate"]
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return None
        
        updates["info_updated_at"] = datetime.now()
        
        with get_db_context() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join(f"{k} = %s" for k in updates.keys())
            values = list(updates.values()) + [fund_code]
            
            cursor.execute(f"""
                UPDATE funds SET {set_clause} WHERE fund_code = %s
            """, values)
            
            return FundService.get_fund_by_code(fund_code)
    
    @staticmethod
    def delete_fund(fund_code: str) -> bool:
        """删除基金（同时删除相关数据）"""
        with get_db_context() as conn:
            cursor = conn.cursor()
            # 删除持仓
            cursor.execute("DELETE FROM holdings WHERE fund_code = %s", (fund_code,))
            # 删除交易记录
            cursor.execute("DELETE FROM trades WHERE fund_code = %s", (fund_code,))
            # 删除价格数据
            cursor.execute("DELETE FROM prices WHERE fund_code = %s", (fund_code,))
            # 删除缓存元数据
            cursor.execute("DELETE FROM cache_meta WHERE fund_code = %s", (fund_code,))
            # 删除基金
            cursor.execute("DELETE FROM funds WHERE fund_code = %s", (fund_code,))
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
            
            # 计算当前市值和当日收益（需要最新净值和涨跌幅）
            cursor.execute("""
                SELECT h.fund_code, h.total_shares, h.total_cost, 
                       f.last_net_value, f.last_growth_rate, f.last_price_date
                FROM holdings h
                LEFT JOIN funds f ON h.fund_code = f.fund_code
            """)
            
            total_market_value = Decimal("0")
            today_profit = Decimal("0")
            
            for row in cursor.fetchall():
                shares = Decimal(str(row["total_shares"]))
                net_value = Decimal(str(row["last_net_value"])) if row["last_net_value"] else Decimal("0")
                growth_rate = Decimal(str(row["last_growth_rate"])) if row["last_growth_rate"] else Decimal("0")
                
                # 当前市值
                market_value = shares * net_value
                total_market_value += market_value
                
                # 当日收益 = 市值 × 涨跌幅 / 100
                # 注意：这是近似计算，对于小幅波动准确
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
            # 检查是否已有持仓
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
            
            # 在同一个连接中查询返回结果（避免事务未提交导致查不到数据）
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
            
            # 使用确认份额更新持仓
            actual_shares = confirm_shares
            if not actual_shares and confirm_net_value and amount:
                actual_shares = amount / confirm_net_value
            
            if actual_shares:
                # 在同一个连接中查询持仓
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
                    # 卖出验证：检查是否有足够份额
                    if not existing:
                        # 删除刚插入的交易记录
                        cursor.execute("DELETE FROM trades WHERE id = %s", (trade_id,))
                        raise ValueError(f"无法卖出：当前未持有该基金")
                    
                    current_shares = Decimal(str(existing["total_shares"]))
                    if current_shares < actual_shares:
                        # 删除刚插入的交易记录
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
                        # 卖光所有份额，删除持仓
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
            # 先获取原交易记录
            cursor.execute(
                "SELECT * FROM trades WHERE id = %s", (trade_id,)
            )
            existing = cursor.fetchone()
            if not existing:
                return None
            
            fund_code = existing["fund_code"]
            
            # 更新字段
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
            
            # 返回更新后的记录
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
    
    @staticmethod
    def recalculate_holding(fund_code: str) -> Optional[dict]:
        """根据交易记录重新计算持仓"""
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
                FundService.delete_holding(fund_code)
                return None
            
            total_shares = Decimal("0")
            total_cost = Decimal("0")
            
            for trade in trades:
                shares = Decimal(str(trade["confirm_shares"] or 0))
                amount = Decimal(str(trade["amount"] or 0))
                
                if trade["trade_type"] == "BUY":
                    total_shares += shares
                    total_cost += amount
                else:  # SELL
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

    @staticmethod
    def get_portfolio_history(days: int = 90) -> dict:
        """获取持仓组合历史收益数据
        
        Args:
            days: 获取最近多少天的数据，默认90天
            
        Returns:
            包含日期、总市值、总成本、累计收益的字典
        """
        from datetime import timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        with get_db_context() as conn:
            cursor = conn.cursor()
            
            # 获取所有持仓基金
            cursor.execute("""
                SELECT h.fund_code, h.total_shares, h.total_cost, f.fund_name
                FROM holdings h
                JOIN funds f ON h.fund_code = f.fund_code
            """)
            holdings = {row["fund_code"]: dict(row) for row in cursor.fetchall()}
            
            if not holdings:
                return {"dates": [], "market_values": [], "costs": [], "profits": [], "profit_rates": []}
            
            # 获取所有持仓基金在日期范围内的净值
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
            
            # 按日期分组计算总市值
            from collections import defaultdict
            daily_prices = defaultdict(dict)
            for p in prices:
                daily_prices[p["date"]][p["fund_code"]] = float(p["net_value"] or 0)
            
            # 获取每只基金的交易记录，用于计算每日成本
            cursor.execute(f"""
                SELECT fund_code, trade_date, trade_type, amount, confirm_shares
                FROM trades
                WHERE fund_code IN ({placeholders})
                AND trade_date <= %s
                ORDER BY trade_date ASC
            """, fund_codes + [end_date])
            
            trades = cursor.fetchall()
            
            # 按基金分组交易记录
            fund_trades = defaultdict(list)
            for t in trades:
                fund_trades[t["fund_code"]].append({
                    "date": t["trade_date"],
                    "type": t["trade_type"],
                    "amount": float(t["amount"] or 0),
                    "shares": float(t["confirm_shares"] or 0)
                })
            
            # 计算每日数据
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
                        # 计算当日持仓份额（考虑交易记录）
                        shares = FundService._calculate_shares_on_date(
                            code, d, float(holding["total_shares"]), fund_trades[code]
                        )
                        
                        value = shares * daily_prices[d][code]
                        daily_market_value += value
                        
                        # 计算当日成本
                        cost = FundService._calculate_cost_on_date(
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
        
        # 从后往前遍历交易，减去之后的交易
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
        
        # 从后往前遍历交易，减去之后的交易
        for trade in reversed(trades):
            if trade["date"] > target_date:
                if trade["type"] == "BUY":
                    cost -= trade["amount"]
                else:
                    # 卖出按成本价加回，这里简化处理
                    cost += trade["amount"]
        
        return max(0, cost)