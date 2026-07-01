"""基金业务服务"""
from datetime import datetime
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
            cursor.execute("DELETE FROM holdings WHERE fund_code = %s", (fund_code,))
            cursor.execute("DELETE FROM trades WHERE fund_code = %s", (fund_code,))
            cursor.execute("DELETE FROM prices WHERE fund_code = %s", (fund_code,))
            cursor.execute("DELETE FROM cache_meta WHERE fund_code = %s", (fund_code,))
            cursor.execute("DELETE FROM funds WHERE fund_code = %s", (fund_code,))
            return cursor.rowcount > 0