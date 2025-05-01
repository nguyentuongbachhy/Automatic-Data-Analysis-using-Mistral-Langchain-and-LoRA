import logging
import time
import os
import psutil
import numpy as np
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import ModelServiceDep, get_performance_monitor
from app.core.config import ModelConfig
from app.models.common import ApiResponse, ResponseStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def health_check() -> ApiResponse:
    """Kiểm tra sức khỏe cơ bản của service"""
    return ApiResponse(
        status=ResponseStatus.SUCCESS,
        data={
            "status": "ok",
            "service": "ai-service"
        }
    )


@router.get("/status", response_model=ApiResponse)
async def service_status(
    model_service: ModelServiceDep,
    performance_monitor = Depends(get_performance_monitor)
) -> ApiResponse:
    """Kiểm tra chi tiết trạng thái của service"""
    try:
        # Lấy thông tin config
        config = ModelConfig().config
        model_config = config.get("model", {})
        
        # Lấy thông tin memory từ model service
        memory_info = model_service.get_memory_info()
        
        # Lấy metrics từ performance monitor
        perf_stats = performance_monitor.get_stats()
        
        # Kiểm tra GPU
        gpu_info = "Not available"
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                devices = []
                for i in range(gpu_count):
                    devices.append({
                        "id": i,
                        "name": torch.cuda.get_device_name(i),
                        "memory_allocated": torch.cuda.memory_allocated(i) / (1024**3),
                        "memory_reserved": torch.cuda.memory_reserved(i) / (1024**3),
                        "memory_total": torch.cuda.get_device_properties(i).total_memory / (1024**3)
                    })
                gpu_info = {
                    "count": gpu_count,
                    "devices": devices
                }
        except Exception as e:
            logger.debug(f"Could not get GPU info: {str(e)}")
        
        # Lấy thông tin hệ thống
        memory = psutil.virtual_memory()
        uptime = time.time() - perf_stats["system"]["uptime_seconds"]
        
        # Lấy thông tin disk
        disk_usage = psutil.disk_usage(os.path.dirname(os.path.abspath(__file__)))
        
        # Tổng hợp status
        status_data = {
            "status": "ok",
            "version": "1.0.0",
            "uptime_seconds": uptime,
            "model": {
                "name": model_config.get("base_model_id", "Unknown"),
                "loaded": memory_info.get("loaded", False),
                "memory_peak_gb": memory_info.get("memory_peak", 0)
            },
            "system": {
                "host": perf_stats["system"]["host"],
                "cpu_count": psutil.cpu_count(),
                "cpu_usage_percent": perf_stats["current"]["cpu"]["current"],
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "memory_usage_percent": memory.percent,
                "disk_total_gb": round(disk_usage.total / (1024**3), 2),
                "disk_free_gb": round(disk_usage.free / (1024**3), 2),
                "disk_usage_percent": disk_usage.percent,
                "gpu": gpu_info
            },
            "performance": {
                "requests": perf_stats["requests"],
                "model": perf_stats["model"]
            }
        }
        # Chuyển đổi NumPy types sang Python native types nếu có
        if hasattr(model_service, '_convert_numpy_types'):
            status_data = model_service._convert_numpy_types(status_data)
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data=status_data
        )
    except Exception as e:
        logger.error(f"Error getting service status: {str(e)}", exc_info=e)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )


@router.post("/clear-cache", response_model=ApiResponse)
async def clear_cache(
    model_service: ModelServiceDep
) -> ApiResponse:
    """Xóa cache của model service"""
    try:
        model_service.clear_cache()
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={
                "status": "ok",
                "message": "Cache cleared successfully"
            }
        )
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}", exc_info=e)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )

@router.get("/metrics", response_model=ApiResponse)
async def get_metrics(
    performance_monitor = Depends(get_performance_monitor)
) -> ApiResponse:
    """Lấy metrics của hệ thống"""
    try:
        metrics = performance_monitor.get_stats()
        
        safe_metrics = {}
        for key, value in metrics.items():
            if isinstance(value, dict):
                safe_metrics[key] = {}
                for k, v in value.items():
                    if isinstance(v, (np.integer, np.floating)):
                        safe_metrics[key][k] = float(v) if isinstance(v, np.floating) else int(v)
                    elif isinstance(v, dict):
                        safe_metrics[key][k] = {}
                        for k2, v2 in v.items():
                            safe_metrics[key][k][k2] = float(v2) if isinstance(v2, (np.integer, np.floating)) else v2
                    else:
                        safe_metrics[key][k] = v
            elif isinstance(value, (np.integer, np.floating)):
                safe_metrics[key] = float(value) if isinstance(value, np.floating) else int(value)
            else:
                safe_metrics[key] = value
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data=safe_metrics
        )
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}", exc_info=e)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )

@router.get("/live", response_model=Dict[str, str])
async def liveness_probe() -> Dict[str, str]:
    """Liveness probe cho Kubernetes"""
    # Đơn giản chỉ kiểm tra service có chạy không
    return {"status": "alive"}


@router.get("/ready", response_model=Dict[str, str])
async def readiness_probe(
    model_service: ModelServiceDep
) -> Dict[str, str]:
    """Readiness probe cho Kubernetes"""
    # Kiểm tra service có sẵn sàng để xử lý requests không
    try:
        # Kiểm tra model đã load chưa
        memory_info = model_service.get_memory_info()
        
        if memory_info.get("loaded", False):
            return {"status": "ready"}
        else:
            # Nếu model chưa load, service chưa sẵn sàng
            raise HTTPException(status_code=503, detail="Model not loaded yet")
    except Exception as e:
        # Trả về 503 Service Unavailable để Kubernetes biết service chưa sẵn sàng
        raise HTTPException(status_code=503, detail=str(e))
