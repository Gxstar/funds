"""请求频率限制器"""
import time
import asyncio
from threading import Lock
from typing import Optional


class RateLimiter:
    """请求频率限制器
    
    用于控制 API 请求频率，避免被封禁
    """
    
    def __init__(self, min_interval: float = 1.0):
        """
        Args:
            min_interval: 最小请求间隔（秒）
        """
        self.min_interval = min_interval
        self.last_request_time: float = 0
        self._lock = Lock()
    
    def acquire(self) -> None:
        """获取请求许可，必要时等待（同步版本）"""
        with self._lock:
            now = time.time()
            wait_time = self.min_interval - (now - self.last_request_time)
            if wait_time > 0:
                time.sleep(wait_time)
            self.last_request_time = time.time()
    
    async def acquire_async(self) -> None:
        """获取请求许可，必要时等待（异步版本）"""
        # 异步版本使用简单的等待
        now = time.time()
        wait_time = self.min_interval - (now - self.last_request_time)
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        with self._lock:
            self.last_request_time = time.time()


class AsyncRateLimiter:
    """异步请求频率限制器"""
    
    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self.last_request_time: float = 0
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """获取请求许可"""
        async with self._lock:
            now = time.time()
            wait_time = self.min_interval - (now - self.last_request_time)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self.last_request_time = time.time()


# 全局 AkShare 限流器实例（1.5 秒间隔）
akshare_limiter = RateLimiter(min_interval=1.5)
