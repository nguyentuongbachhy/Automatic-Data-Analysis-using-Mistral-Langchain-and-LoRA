import time
from typing import Dict, Any, Callable, Optional, Tuple
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.models.common import ApiResponse, ResponseStatus

class RateLimiter(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(
        self, 
        app,
        max_requests: int = 100,
        time_window: int = 60,  # seconds
        by_ip: bool = True
    ):
        """Initialize rate limiter middleware"""
        super().__init__(app)
        self.max_requests = max_requests
        self.time_window = time_window
        self.by_ip = by_ip
        self.requests: Dict[str, Dict[str, Any]] = {}
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and apply rate limiting"""
        # Get client identifier
        if self.by_ip:
            client_id = request.client.host
        else:
            # Could use a header or token for identification
            client_id = request.headers.get("X-API-Key", request.client.host)
            
        # Check for rate limit
        current_time = time.time()
        is_rate_limited, retry_after = self._check_rate_limit(client_id, current_time)
        
        if is_rate_limited:
            # Return rate limit response
            error_response = ApiResponse(
                status=ResponseStatus.ERROR,
                error="Rate limit exceeded",
                meta={"retry_after": retry_after}
            )
            
            response = JSONResponse(
                status_code=429,
                content=error_response.model_dump()
            )
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(self.max_requests)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(retry_after + current_time))
            response.headers["Retry-After"] = str(int(retry_after))
            
            return response
            
        # Update request counter
        self._update_request_count(client_id, current_time)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        remaining = self.max_requests - self.requests[client_id]["count"]
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        
        return response
        
    def _check_rate_limit(self, client_id: str, current_time: float) -> Tuple[bool, float]:
        """Check if client is rate limited, returns (is_limited, retry_after)"""
        if client_id not in self.requests:
            return False, 0
            
        client_data = self.requests[client_id]
        window_start = client_data["start_time"]
        
        # Reset window if it has expired
        if current_time - window_start > self.time_window:
            return False, 0
            
        # Check if limit reached
        if client_data["count"] >= self.max_requests:
            # Calculate time until window reset
            retry_after = self.time_window - (current_time - window_start)
            return True, retry_after
            
        return False, 0
        
    def _update_request_count(self, client_id: str, current_time: float):
        """Update request count for client"""
        if client_id not in self.requests:
            self.requests[client_id] = {
                "count": 1,
                "start_time": current_time
            }
        else:
            # Check if we need to reset the window
            if current_time - self.requests[client_id]["start_time"] > self.time_window:
                self.requests[client_id] = {
                    "count": 1,
                    "start_time": current_time
                }
            else:
                self.requests[client_id]["count"] += 1
                
    def _cleanup_old_entries(self, current_time: float):
        """Remove expired entries to prevent memory leak"""
        expired_clients = []
        
        for client_id, data in self.requests.items():
            if current_time - data["start_time"] > self.time_window * 2:
                expired_clients.append(client_id)
                
        for client_id in expired_clients:
            del self.requests[client_id]