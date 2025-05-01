ai-service/
├── app/                              # Application code
|   ├── api/                          # API layer
|   │   ├── routers/                  # FastAPI routers
|   │   │   ├── analyze_router.py     # API endpoints cho phân tích
|   │   │   ├── chat_router.py        # API endpoints cho chat
|   │   │   └── health_router.py      # Health check API
|   │   ├── middleware/               # Middleware API
|   │   │   ├── error_handler.py      # Xử lý lỗi
|   │   │   ├── auth.py               # Xác thực
|   │   │   └── rate_limiter.py       # Giới hạn rate
|   │   ├── dependencies.py           # Dependency injection
|   │   └── __init__.py
|   ├── core/                         # Core application settings
|   │   ├── config.py                 # Configuration handler
|   │   ├── logging.py                # Logging configuration
|   │   ├── errors.py                 # Error handling
|   │   ├── cache.py                  # Cache management
|   │   ├── monitoring.py             # Performance monitoring
|   │   ├── tasks.py                  # Background tasks
|   │   └── __init__.py
|   ├── models/                       # Pydantic models
|   │   ├── analysis.py               # Analysis models
|   │   ├── chat.py                   # Chat models
|   │   ├── common.py                 # Shared models
|   │   └── __init__.py
|   ├── services/                     # Business logic services
|   │   ├── analyze_service.py        # Analyze service
|   │   ├── chat_service.py           # Chat service
|   │   ├── model_service.py          # Model inference service
|   │   ├── validation_service.py     # Data validation
|   │   ├── intent_service.py         # Intent detection
|   │   ├── base_service.py           # Base service
|   │   └── __init__.py
|   ├── utils/                        # Utilities
|   │   ├── file_utils.py             # File handling
|   │   ├── serialization.py          # Object serialization
|   │   ├── profiler.py               # Performance profiling
|   │   └── __init__.py
|   ├── main.py                       # Application entry point
|   └──dependencies.py
├── ml/                               # ML library code
|   ├── data/                         # Data processing
|   │   ├── data_processor.py         # Cleaning, processing and transform
|   │   ├── data_validator.py         # Data validation
|   │   └── __init__.py
|   ├── model/                        # Model handling
|   │   ├── model.py                  # Manage model and configuration of model
|   │   └── __init__.py
|   ├── analysis/                     # Analysis components
|   │   ├── analyzer.py               # Auto analyze with advanced ML/DL
|   │   ├── time_series.py            # Analyze and predict advanced time-series
|   │   └── __init__.py
|   ├── visualization/                # Visualization
|   │   ├── charts.py                 # Advanced generator charts
|   │   ├── insights.py               # Generator insights from dataframe using Mistral AI
|   │   ├── recommender.py            # Recommend charts for each datatype
|   │   └── __init__.py
|   ├── utils/                        # ML-specific utilities
|   │   ├── datetime_utils.py         # DateTime utilities
|   │   ├── memory_utils.py           # Memory optimization
|   │   └── __init__.py
|   └── __init__.py
└── configs/                          # Configuration files
    ├── model_config.json             # Model configuration
    ├── logging_config.json           # Logging configuration
    └── plugins_config.json           # Plugins configuration