"""数据同步调度器"""
import asyncio
from datetime import datetime, date
from typing import Set
import logging

from services.fund_service import FundService
from services.market_service import MarketService

logger = logging.getLogger(__name__)


class SyncScheduler:
    """后台同步调度器
    
    每日两次同步：
    - 14:50 盘中决策同步
    - 15:30 收盘后同步
    """
    
    SYNC_TIMES = ["14:50", "15:30"]
    
    def __init__(self):
        self._running = False
        self._synced_today: Set[str] = set()
        self._task: asyncio.Task = None
    
    async def start(self):
        """启动定时同步"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("同步调度器已启动")
    
    async def stop(self):
        """停止定时同步"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("同步调度器已停止")
    
    async def _run(self):
        """主循环"""
        while self._running:
            try:
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                today = date.today().isoformat()
                
                # 检查是否需要重置（新的一天）
                if current_time == "00:00":
                    self._synced_today.clear()
                    logger.info("新的一天，重置同步状态")
                
                # 检查是否到达同步时间
                for sync_time in self.SYNC_TIMES:
                    sync_key = f"{today}_{sync_time}"
                    if current_time == sync_time and sync_key not in self._synced_today:
                        logger.info(f"开始定时同步: {sync_time}")
                        await self.sync_all_funds()
                        self._synced_today.add(sync_key)
                
                # 每30秒检查一次
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"同步调度器错误: {e}")
                await asyncio.sleep(60)
    
    async def sync_all_funds(self):
        """同步所有持仓基金"""
        try:
            funds = FundService.get_all_funds()
            
            for fund in funds:
                try:
                    result = await MarketService.sync_fund_history(fund["fund_code"])
                    logger.info(f"同步基金 {fund['fund_code']}: {result.get('status')}")
                except Exception as e:
                    logger.error(f"同步基金 {fund['fund_code']} 失败: {e}")
                
                # 限流
                await asyncio.sleep(1.5)
            
            logger.info("所有基金同步完成")
        except Exception as e:
            logger.error(f"批量同步失败: {e}")
    
    async def sync_on_startup(self):
        """启动时同步"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        # 只在工作时间内启动同步
        # 如果当前时间在 9:00 - 20:00 之间，则执行启动同步
        if "09:00" <= current_time <= "20:00":
            logger.info("启动时同步数据...")
            await self.sync_all_funds()


# 全局调度器实例
scheduler = SyncScheduler()
