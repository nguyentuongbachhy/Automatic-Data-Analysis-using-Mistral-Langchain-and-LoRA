from fastapi import HTTPException, status

class AIServiceError(Exception):
    """Base exception class for AI-service"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Internal server error"
    
    def __init__(self, detail=None, status_code=None):
        self.detail = detail or self.detail
        self.status_code = status_code or self.status_code
        super().__init__(self.detail)
    
    def to_http_exception(self):
        """Convert to FastAPI HTTPException"""
        return HTTPException(
            status_code=self.status_code,
            detail=self.detail
        )

class ModelError(AIServiceError):
    """Errors related to model loading or inference"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = "Model error"

class DataProcessingError(AIServiceError):
    """Errors related to data processing"""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Data processing error"

class FileError(AIServiceError):
    """Errors related to file operations"""
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "File error"

class ValidationError(AIServiceError):
    """Errors related to data validation"""
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Validation error"

class ResourceExhaustedError(AIServiceError):
    """Errors related to resource exhaustion"""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    detail = "Resource exhausted"