import logging
import json
import os
import sys
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.services.model_service import ModelService

# Thêm thư mục gốc vào PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Bây giờ import các module
from app.api.routers import analyze_router, chat_router, health_router
from app.services.model_service import ModelService
from app.core.config import ModelConfig
from app.core.errors import AIServiceError
from app.core.cache import InferenceCache
from app.utils.json_encoder import configure_custom_json_serialization

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up ML Service")
    try:
        config = ModelConfig()
        cache_config = config.get_cache_config()
        ttl = cache_config.get("ttl_seconds", 3600)
        max_size = cache_config.get("max_size_mb", 512)
        cache = InferenceCache(ttl_seconds=ttl, max_size=max_size)

        logger.info("Loading model...")

        ModelService.get_instance(config, cache)
        logger.info("Model loaded successfully")
        yield
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}", exc_info=e)
        raise
    finally:
        logger.info("Shutting down ML Service")


# Tạo FastAPI app
app = FastAPI(
    title="DataSenseAI ML Service",
    description="ML Service cho hệ thống DataSenseAI",
    version="1.0.0",
    lifespan=lifespan
)

# Áp dụng cấu hình serialization tùy chỉnh
app = configure_custom_json_serialization(app)

# Thêm CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware để log request và thêm serialization bổ sung
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Custom exception handler
@app.exception_handler(AIServiceError)
async def ai_service_error_handler(request: Request, exc: AIServiceError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail}
    )

# Register routers
app.include_router(health_router.router, prefix="/health", tags=["Health"])
app.include_router(analyze_router.router, prefix="/analyze", tags=["Analysis"])
app.include_router(chat_router.router, prefix="/chat", tags=["Chat"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)