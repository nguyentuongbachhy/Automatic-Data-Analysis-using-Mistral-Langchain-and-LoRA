import logging
from typing import Dict, Any, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.models.common import ApiResponse, ResponseStatus

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle errors globally"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle any exceptions"""
        try:
            return await call_next(request)
        except Exception as e:
            # Log the error
            logger.exception(f"Unhandled exception: {str(e)}")
            
            # Determine status code
            status_code = 500
            if hasattr(e, "status_code"):
                status_code = e.status_code
                
            # Create error response
            error_response = ApiResponse(
                status=ResponseStatus.ERROR,
                error=str(e)
            )
            
            # Return JSON response
            return JSONResponse(
                status_code=status_code,
                content=error_response.model_dump()
            )