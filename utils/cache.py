"""通用 TTL 内存缓存"""
import time
import threading
from typing import Optional, TypeVar, Generic

T = TypeVar("T")


class TTLCache(Generic[T]):
    """线程安全的 TTL 缓存。不感知交易时间，调用方自行决定 TTL。"""

    def __init__(self, ttl: float):
        self._ttl = ttl
        self._data: Optional[T] = None
        self._timestamp: float = 0
        self._lock = threading.Lock()

    def get(self) -> Optional[T]:
        with self._lock:
            if self._data is not None and time.monotonic() - self._timestamp < self._ttl:
                return self._data
        return None

    def set(self, data: T):
        with self._lock:
            self._data = data
            self._timestamp = time.monotonic()

    def invalidate(self):
        with self._lock:
            self._data = None
            self._timestamp = 0
