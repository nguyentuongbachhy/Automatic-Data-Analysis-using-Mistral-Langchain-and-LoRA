import time
import logging
import threading
from typing import Dict, Any, Optional
import json

logger = logging.getLogger(__name__)

class LRUCacheItem:
    """Item trong LRU cache với tracking truy cập mới nhất"""
    def __init__(self, key: str, value: Any, expire_time: float, size_bytes: int = 0):
        self.key = key
        self.value = value
        self.expire_time = expire_time
        self.last_access_time = time.time()
        self.size_bytes = size_bytes

class InferenceCache:
    """
    Cache service cải tiến với khả năng:
    - LRU eviction
    - Memory limit monitoring
    - TTL expiration
    - Stats tracking
    """
    def __init__(
        self, 
        ttl_seconds: int = 3600,
        max_size: int = 512,  # MB
        cleanup_interval: int = 300,  # seconds
    ):
        self.cache: Dict[str, LRUCacheItem] = {}
        self.ttl_seconds = ttl_seconds
        self.max_size_bytes = max_size * 1024 * 1024  # Convert to bytes
        self.current_size_bytes = 0
        self.cleanup_interval = cleanup_interval

        # Thống kê
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.expirations = 0
        
        # Lock thread-safety
        self._lock = threading.RLock()
        
        # Thời gian dọn dẹp cuối cùng
        self.last_cleanup_time = time.time()
        
        # Background cleanup
        self._start_cleanup_thread()
        
        logger.info(f"Initialized InferenceCache: TTL={ttl_seconds}s, Max size={max_size}MB")

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if exists and not expired"""
        with self._lock:
            # Kiểm tra key tồn tại
            if key not in self.cache:
                self.misses += 1
                return None
            
            # Kiểm tra expired
            current_time = time.time()
            cache_item = self.cache[key]
            if current_time > cache_item.expire_time:
                self._remove_item(key)
                self.misses += 1
                self.expirations += 1
                return None

            # Cập nhật thời gian truy cập
            cache_item.last_access_time = current_time
            self.hits += 1
            return cache_item.value

    def set(self, key: str, value: Any) -> None:
        """Set value in cache with TTL"""
        with self._lock:
            # Tính kích thước của value
            size_bytes = self._estimate_size(value)
            
            # Kiểm tra xem cache có đủ không gian không
            if size_bytes > self.max_size_bytes:
                logger.warning(f"Cache item too large: {size_bytes} bytes > {self.max_size_bytes} bytes")
                return
                
            # Tính thời gian hết hạn
            expire_time = time.time() + self.ttl_seconds
            
            # Xóa key cũ nếu tồn tại
            if key in self.cache:
                old_size = self.cache[key].size_bytes
                self.current_size_bytes -= old_size
                
            # Tạo cache item mới
            cache_item = LRUCacheItem(key, value, expire_time, size_bytes)
            
            # Kiểm tra không gian và evict các item cũ nếu cần
            while self.current_size_bytes + size_bytes > self.max_size_bytes:
                self._evict_lru_item()
                
            # Lưu vào cache
            self.cache[key] = cache_item
            self.current_size_bytes += size_bytes

    def clear(self) -> None:
        """Clear all cache"""
        with self._lock:
            self.cache.clear()
            self.current_size_bytes = 0
            logger.info("Cache cleared")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "size_items": len(self.cache),
                "size_bytes": self.current_size_bytes,
                "size_mb": round(self.current_size_bytes / (1024 * 1024), 2),
                "max_size_mb": round(self.max_size_bytes / (1024 * 1024), 2),
                "utilization_percent": round(self.current_size_bytes / self.max_size_bytes * 100, 2) if self.max_size_bytes > 0 else 0,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_percent": round(hit_rate, 2),
                "evictions": self.evictions,
                "expirations": self.expirations,
                "ttl_seconds": self.ttl_seconds
            }
    
    def _estimate_size(self, obj: Any) -> int:
        """Estimate size of object in bytes"""
        try:
            # Với các kiểu dữ liệu cơ bản
            if isinstance(obj, (str, bytes, bytearray)):
                return len(obj)
            
            # Với các đối tượng json-serializable
            json_str = json.dumps(obj)
            return len(json_str.encode('utf-8'))
        except:
            # Fallback estimate
            import sys
            return sys.getsizeof(obj)
        
    def _evict_lru_item(self) -> None:
        """Evict least recently used item from cache"""
        if not self.cache:
            return
            
        # Tìm item được truy cập gần đây nhất
        lru_key = min(self.cache.items(), key=lambda x: x[1].last_access_time)[0]
        
        # Xóa item khỏi cache
        self._remove_item(lru_key)
        self.evictions += 1
        
    def _remove_item(self, key: str) -> None:
        """Remove item from cache và update size tracking"""
        if key in self.cache:
            size_bytes = self.cache[key].size_bytes
            self.current_size_bytes -= size_bytes
            del self.cache[key]
            
    def _cleanup_expired(self) -> int:
        """Remove all expired items from cache, returns count of removed items"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, item in self.cache.items() 
                if current_time > item.expire_time
            ]
            
            for key in expired_keys:
                self._remove_item(key)
                self.expirations += 1
                
            return len(expired_keys)
            
    def _cleanup_thread(self):
        """Background thread for periodic cleanup"""
        while True:
            time.sleep(self.cleanup_interval)
            try:
                current_time = time.time()
                if current_time - self.last_cleanup_time > self.cleanup_interval:
                    count = self._cleanup_expired()
                    if count > 0:
                        logger.debug(f"Cache cleanup: removed {count} expired items")
                    self.last_cleanup_time = current_time
            except Exception as e:
                logger.error(f"Error in cache cleanup thread: {str(e)}")
            
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        thread = threading.Thread(target=self._cleanup_thread)
        thread.daemon = True
        thread.start()