## Cấu trúc thư mục
```ascii
data-analyzer-ai/
│
├── apps/                         # Application
│   ├── client/                   # Frontend (Vite + React + TS)
│   │   ├── public/
│   │   ├── src/
│   │   │   ├── components/       # React components
│   │   │   │   ├── ui/           # Components re-utilities
│   │   │   │   ├── chat/         # Interface of chat
│   │   │   │   ├── upload/       # Upload files
│   │   │   │   ├── visualization/ # Components of visualization
│   │   │   │   ├── insights/     # Components of insights
│   │   │   │   └── layout/       # Components of layout
│   │   │   │
│   │   │   ├── hooks/            # React hooks customization
│   │   │   ├── services/         # Service API
│   │   │   ├── utils/            # Function utilities
│   │   │   ├── types/            # Definition types
│   │   │   ├── contexts/         # React contexts
│   │   │   ├── App.tsx           # Component App
│   │   │   └── main.tsx          # Entry point
│   │   │
│   │   ├── tailwind.config.js    # Configuration of Tailwind
│   │   ├── tsconfig.json
│   │   ├── vite.config.ts
│   │   └── package.json
│   │
│   ├── server/                   # Backend API (Node.js/Express)
│   │   ├── src/
│   │   │   ├── controllers/      # Controllers of routes
│   │   │   ├── services/         # Logics of business
│   │   │   │   ├── analyzeService.ts   # Service analyze
│   │   │   │   ├── chatService.ts      # Service chat
│   │   │   │   ├── mlService.ts        # Communication with ML
│   │   │   │   └── visualizeService.ts # Service visualization
│   │   │   │
│   │   │   ├── middlewares/      # Middlewares Express
│   │   │   │   ├── upload.ts     # Middleware de upload
│   │   │   │   └── auth.ts       # Authentication
│   │   │   │
│   │   │   ├── utils/            # Function utilities
│   │   │   │   ├── fileUtils.ts  # Utilities for files
│   │   │   │   └── dataUtils.ts  # Utilities for data
│   │   │   │
│   │   │   ├── routes/           # Routes API
│   │   │   ├── types/            # Definition types
│   │   │   ├── config/           # Configuration
│   │   │   ├── lib/              # Libraries
│   │   │   │   ├── prisma.ts     # Client Prisma
│   │   │   │   └── socket.ts     # Configuration Socket.io
│   │   │   │
│   │   │   ├── app.ts            # Configuration Express
│   │   │   └── index.ts          # Entry point
│   │   │
│   │   ├── uploads/              # Directory uploads temporation
│   │   ├── prisma/               # Schema Prisma
│   │   │   └── schema.prisma
│   │   │
│   │   ├── tsconfig.json
│   │   └── package.json
│   │
│   └── ai-service/
│       ├── app/                              # Application code
|       |   ├── api/                          # API layer
|       |   │   ├── routers/                  # FastAPI routers
|       |   │   │   ├── analyze_router.py     # API endpoints cho phân tích
|       |   │   │   ├── chat_router.py        # API endpoints cho chat
|       |   │   │   └── health_router.py      # Health check API
|       |   │   ├── middleware/               # Middleware API
|       |   │   │   ├── error_handler.py      # Xử lý lỗi
|       |   │   │   ├── auth.py               # Xác thực
|       |   │   │   └── rate_limiter.py       # Giới hạn rate
|       |   │   ├── dependencies.py           # Dependency injection
|       |   │   └── __init__.py
|       |   ├── core/                         # Core application settings
|       |   │   ├── config.py                 # Configuration handler
|       |   │   ├── logging.py                # Logging configuration
|       |   │   ├── errors.py                 # Error handling
|       |   │   ├── cache.py                  # Cache management
|       |   │   ├── monitoring.py             # Performance monitoring
|       |   │   ├── tasks.py                  # Background tasks
|       |   │   └── __init__.py
|       |   ├── models/                       # Pydantic models
|       |   │   ├── analysis.py               # Analysis models
|       |   │   ├── chat.py                   # Chat models
|       |   │   ├── common.py                 # Shared models
|       |   │   └── __init__.py
|       |   ├── services/                     # Business logic services
|       |   │   ├── analyze_service.py        # Analyze service
|       |   │   ├── chat_service.py           # Chat service
|       |   │   ├── model_service.py          # Model inference service
|       |   │   ├── validation_service.py     # Data validation
|       |   │   ├── intent_service.py         # Intent detection
|       |   │   └── __init__.py
|       |   ├── utils/                        # Utilities
|       |   │   ├── file_utils.py             # File handling
|       |   │   ├── serialization.py          # Object serialization
|       |   │   ├── profiler.py               # Performance profiling
|       |   │   └── __init__.py
|       |   └── main.py                       # Application entry point
│       ├── ml/                               # ML library code
|       |   ├── data/                         # Data processing
|       |   │   ├── data_processor.py         # Cleaning, processing and transform
|       |   │   ├── data_validator.py         # Data validation
|       |   │   └── __init__.py
|       |   ├── model/                        # Model handling
|       |   │   ├── model.py                  # Manage model and configuration of model
|       |   │   └── __init__.py
|       |   ├── analysis/                     # Analysis components
|       |   │   ├── analyzer.py               # Auto analyze with advanced ML/DL
|       |   │   ├── time_series.py            # Analyze and predict advanced time-series
|       |   │   └── __init__.py
|       |   ├── visualization/                # Visualization
|       |   │   ├── charts.py                 # Advanced generator charts
|       |   │   ├── insights.py               # Generator insights from dataframe using Mistral AI
|       |   │   ├── recommender.py            # Recommend charts for each datatype
|       |   │   └── __init__.py
|       |   ├── utils/                        # ML-specific utilities
|       |   │   ├── datetime_utils.py         # DateTime utilities
|       |   │   ├── memory_utils.py           # Memory optimization
|       |   │   └── __init__.py
|       |   └── __init__.py
│       └── configs/                          # Configuration files
│           ├── model_config.json             # Model configuration
│           ├── logging_config.json           # Logging configuration
│           └── plugins_config.json           # Plugins configuration
│
├── docker/                       # Configuration Docker
│   ├── client.Dockerfile
│   ├── server.Dockerfile
│   ├── ml-service.Dockerfile
│   └── nginx.conf
│
├── docker-compose.yml           # Configuration Docker Compose
├── package.json                 # Root package.json
├── pnpm-workspace.yaml          # Configuration workspace pnpm
└── README.md                    # Documentation
```