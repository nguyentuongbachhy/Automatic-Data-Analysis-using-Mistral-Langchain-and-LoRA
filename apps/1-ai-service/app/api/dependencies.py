from typing import Annotated, Callable
import functools

from fastapi import Depends

from app.core.config import ModelConfig
from app.services.model_service import ModelService
from app.services.analyze_service import AnalyzeService
from app.services.chat.chat_service import ChatService
from app.services.streaming.streaming_manager import StreamingManager
from app.services.validation_service import ValidationService
from app.services.intent_service import IntentDetectionService
from app.core.monitoring import PerformanceMonitor
from app.core.cache import InferenceCache

_model_config = None
_model_service = None
_intent_service = None
_performance_monitor = None
_inference_cache = None


def get_config() -> ModelConfig:
    """Get model configuration singleton"""
    global _model_config
    if _model_config is None:
        _model_config = ModelConfig()
    return _model_config

def get_inference_cache() -> InferenceCache:
    """Get inference cache singleton"""
    global _inference_cache
    if _inference_cache is None:
        config = get_config()
        cache_config = config.get_cache_config()
        ttl = cache_config.get("ttl_seconds", 3600)
        max_size = cache_config.get("max_size_mb", 512)
        _inference_cache = InferenceCache(ttl_seconds=ttl, max_size=max_size)
    return _inference_cache

def get_model_service() -> ModelService:
    """Get model service singleton"""
    global _model_service
    if _model_service is None:
        config = get_config()
        cache = get_inference_cache()
        _model_service = ModelService.get_instance(config=config.config, cache=cache)
    return _model_service

def get_intent_service() -> IntentDetectionService:
    """Get intent detection service singleton"""
    global _intent_service
    if _intent_service is None:
        config = get_config()
        _intent_service = IntentDetectionService.get_instance(config=config.config)
    return _intent_service

def get_validation_service() -> ValidationService:
    """Get validation service"""
    return ValidationService().get_instance()

def get_chat_service(
    model_service: ModelService = Depends(get_model_service),
    intent_service: IntentDetectionService = Depends(get_intent_service),
    validation_service: ValidationService = Depends(get_validation_service),
    inference_cache: InferenceCache = Depends(get_inference_cache)
) -> ChatService:
    """Get chat service with dependencies"""
    config = get_config()
    return ChatService(model_service=model_service, intent_service=intent_service, validation_service=validation_service, config=config, cache=inference_cache)

def get_analyze_service(
    file_id: str,
    user_id: str,
    model_service: ModelService = Depends(get_model_service)
) -> AnalyzeService:
    """Get analyze service with dependencies"""
    config = get_config()
    return AnalyzeService(
        file_id=file_id,
        user_id=user_id,
        model_service=model_service,
        config=config
    )

def get_performance_monitor() -> PerformanceMonitor:
    """Get performance monitor singleton"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor.get_instance()
    return _performance_monitor

ModelConfigDep = Annotated[ModelConfig, Depends(get_config)]
ModelServiceDep = Annotated[ModelService, Depends(get_model_service)]
ValidationServiceDep = Annotated[ValidationService, Depends(get_validation_service)]
IntentServiceDep = Annotated[IntentDetectionService, Depends(get_intent_service)]
CacheDep = Annotated[InferenceCache, Depends(get_inference_cache)]
PerformanceMonitorDep = Annotated[PerformanceMonitor, Depends(get_performance_monitor)]

def timed_endpoint(route_func: Callable):
    """Decorator to time endpoint execution and record metrics"""
    @functools.wraps(route_func)
    async def wrapper(*args, **kwargs):
        import time
        
        monitor = get_performance_monitor()
        start_time = time.time()
        success = True
        
        try:
            response = await route_func(*args, **kwargs)
            return response
        except Exception as e:
            success = False
            raise
        finally:
            duration = time.time() - start_time
            monitor.record_request(duration=duration, success=success)
            
    return wrapper