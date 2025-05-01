from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
import pandas as pd
import numpy as np
import json
from datetime import datetime
from pydantic import BaseModel, Field, model_validator

def pandas_json_serializer(obj):
    """Custom JSON serializer cho các đối tượng pandas và numpy"""
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    elif isinstance(obj, pd.Series):
        return obj.tolist()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, (datetime, np.datetime64)):
        return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
    elif isinstance(obj, set):
        return list(obj)
    elif hasattr(obj, 'model_dump'):
        return obj.model_dump()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

class ResponseStatus(str, Enum):
    """Status của API response"""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"

class ApiResponse(BaseModel):
    """Base API response model"""
    status: ResponseStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            pd.DataFrame: lambda df: df.to_dict(orient="records"),
            pd.Series: lambda s: s.tolist(),
            np.ndarray: lambda arr: arr.tolist(),
        }
        
    def model_dump(self, **kwargs):
        """Override model_dump để xử lý các đối tượng đặc biệt"""
        json_str = json.dumps(super().model_dump(**kwargs), default=pandas_json_serializer)
        return json.loads(json_str)
    
    def model_dump_json(self, **kwargs):
        """Override model_dump_json để xử lý các đối tượng đặc biệt"""
        return json.dumps(self.model_dump(**kwargs))
    
    @model_validator(mode='after')
    def check_data_or_error(self):
        """Đảm bảo data hoặc error được set, không cả hai"""
        status = self.status
        data = self.data
        error = self.error
        
        if status == ResponseStatus.SUCCESS and not data:
            self.data = {}
            
        if status == ResponseStatus.ERROR and not error:
            self.error = "Unknown error"
            
        return self

class PaginatedResponse(ApiResponse):
    """Response with pagination"""
    page: int = 1
    page_size: int = 10
    total: int = 0
    total_pages: int = 0
    
    @model_validator(mode='after')
    def calculate_total_pages(self):
        """Tính total_pages dựa trên total và page_size"""
        total = self.total
        page_size = self.page_size
        
        if page_size > 0:
            self.total_pages = (total + page_size - 1) // page_size
        else:
            self.total_pages = 0
            
        return self

class UploadResponse(ApiResponse):
    """Response for file upload"""
    file_id: str
    file_path: str
    file_name: str
    file_size: int
    mime_type: str
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "file_id": "f43a7b25-3d7a-4a9f-8c48-4b9726abcdef",
                "file_path": "/tmp/uploads/f43a7b25-3d7a-4a9f-8c48-4b9726abcdef_data.csv",
                "file_name": "data.csv",
                "file_size": 1048576,
                "mime_type": "text/csv"
            }
        }

class FileInfo(BaseModel):
    """Information about a file"""
    file_id: str
    file_name: str
    file_path: str
    file_size: int
    mime_type: str
    upload_date: str
    num_rows: Optional[int] = None
    num_columns: Optional[int] = None
    column_types: Optional[Dict[str, List[str]]] = None
    data_quality: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "file_id": "f43a7b25-3d7a-4a9f-8c48-4b9726abcdef",
                "file_name": "sales_data.csv",
                "file_path": "/tmp/uploads/f43a7b25-3d7a-4a9f-8c48-4b9726abcdef_sales_data.csv",
                "file_size": 1048576,
                "mime_type": "text/csv",
                "upload_date": "2025-04-10T10:30:45.123Z",
                "num_rows": 1000,
                "num_columns": 10,
                "column_types": {
                    "numeric": ["revenue", "quantity", "price"],
                    "categorical": ["product", "category", "region"],
                    "datetime": ["date"]
                }
            }
        }

class ColumnInfo(BaseModel):
    """Information about a data column"""
    name: str
    display_name: str
    type: str
    stats: Dict[str, Any]
    completeness: float
    quality: float
    nullable: bool
    
    class Config:
        schema_extra = {
            "example": {
                "name": "revenue",
                "display_name": "Revenue",
                "type": "numeric",
                "stats": {
                    "count": 1000,
                    "mean": 5432.1,
                    "std": 1234.5,
                    "min": 100,
                    "max": 10000
                },
                "completeness": 98.5,
                "quality": 95.2,
                "nullable": True
            }
        }

class ErrorDetail(BaseModel):
    """Detailed error information"""
    code: str
    message: str
    location: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "code": "file_not_found",
                "message": "The requested file could not be found",
                "location": "path",
                "details": {
                    "file_id": "f43a7b25-3d7a-4a9f-8c48-4b9726abcdef",
                    "attempted_path": "/tmp/uploads/f43a7b25-3d7a-4a9f-8c48-4b9726abcdef_data.csv"
                }
            }
        }

class ErrorResponse(ApiResponse):
    """Enhanced error response with error details"""
    status: ResponseStatus = ResponseStatus.ERROR
    error: str
    error_details: Optional[ErrorDetail] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "error": "File not found",
                "error_details": {
                    "code": "file_not_found",
                    "message": "The requested file could not be found",
                    "location": "path",
                    "details": {
                        "file_id": "f43a7b25-3d7a-4a9f-8c48-4b9726abcdef"
                    }
                }
            }
        }

class SuccessResponse(ApiResponse):
    """Standard success response"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    data: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "message": "Operation completed successfully"
                }
            }
        }

class MLServiceRequest(BaseModel):
    """Request model for ML service APIs"""
    file_id: Optional[str] = None
    user_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "fileId": "f43a7b25-3d7a-4a9f-8c48-4b9726abcdef",
                "query": "Show me the trend of revenue over time",
                "data": {
                    "date_column": "date",
                    "value_column": "revenue",
                    "forecast": True,
                    "forecast_periods": 10
                }
            }
        }

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    uptime: float
    checks: Dict[str, Dict[str, Any]]
    
    class Config:
        schema_extra = {
            "example": {
                "status": "ok",
                "version": "1.0.0",
                "uptime": 3600.5,
                "checks": {
                    "database": {
                        "status": "ok",
                        "latency_ms": 5.2
                    },
                    "model": {
                        "status": "ok",
                        "loaded": True,
                        "memory_usage_mb": 2048
                    },
                    "disk": {
                        "status": "ok",
                        "free_space_mb": 10240
                    }
                }
            }
        }