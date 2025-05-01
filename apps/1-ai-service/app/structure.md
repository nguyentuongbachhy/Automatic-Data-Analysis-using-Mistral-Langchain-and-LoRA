# Cấu trúc thư mục

├── __init__.py
├── api
│   ├── __init__.py
│   ├── dependencies.py
│   ├── middleware
│   │   ├── auth.py
│   │   ├── error_handler.py
│   │   └── rate_limiter.py
│   └── routers
│       ├── __init__.py
│       ├── analyze_router.py
│       ├── chat_router.py
│       └── health_router.py
├── core
│   ├── __init__.py
│   ├── cache.py
│   ├── config.py
│   ├── errors.py
│   ├── logging.py
│   ├── monitoring.py
│   └── tasks.py
├── main.py
├── models
│   ├── __init__.py
│   ├── analysis.py
│   ├── chat.py
│   └── common.py
├── services
│   ├── __init__.py
│   ├── analyze_service.py
│   ├── base_service.py
│   ├── chat
│   │   ├── __init__.py
│   │   └── chat_service.py
│   ├── intent_service.py
│   ├── model_service.py
│   ├── streaming
│   │   ├── __init__.py
│   │   └── streaming_manager.py
│   └── validation_service.py
└── utils
    ├── __init__.py
    ├── file_utils.py
    ├── json_encoder.py
    └── profiler.py