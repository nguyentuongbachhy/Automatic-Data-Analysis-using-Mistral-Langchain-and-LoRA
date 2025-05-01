// Giữ các enum từ phần đầu
export enum ResponseStatus {
    SUCCESS = "success",
    ERROR = "error",
    PENDING = "pending"
}

export enum InsightType {
    CORRELATION = "correlation",
    TREND = "trend",
    DISTRIBUTION = "distribution",
    OUTLIER = "outlier",
    SUMMARY = "summary",
    PATTERN = "pattern",
    ANOMALY = "anomaly",
    COMPARISON = "comparison"
}

export enum ChartType {
    LINE = "line",
    BAR = "bar",
    SCATTER = "scatter",
    PIE = "pie",
    HISTOGRAM = "histogram",
    GROUPED_HISTOGRAM = "grouped histogram",
    BOX = "box",
    HEATMAP = "heatmap",
    AREA = "area",
    BUBBLE = "bubble",
    RADAR = "radar",
    COMBO = "combo",
    WATERFALL = "waterfall",
    TREEMAP = "treemap",
    SANKEY = "sankey"
}

export enum MessageRole {
    SYSTEM = "system",
    USER = "user",
    ASSISTANT = "assistant"
}

export enum IntentType {
    QUESTION = "question",
    VISUALIZATION = "visualization",
    ANALYSIS = "analysis",
    INSIGHT = "insight",
    PREDICTION = "prediction",
    UNKNOWN = "unknown"
}

// Interface cơ bản
export interface ApiResponse<T = any> {
    status: ResponseStatus;
    data?: T;
    error?: string;
    meta?: Record<string, any>;
}

export interface PaginatedResponse<T = any> extends ApiResponse<T> {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
}

// Phần chat và message
export interface ChatMessage {
    role: MessageRole;
    content: string;
}

export interface ChatRequest {
    query: string;
    userId: string;
    chatId: string;
    fileId?: string;
    useCache?: boolean;
}

export interface ChatResponse {
    response: string;
    visualizations?: VisualizationData[];
    insights?: InsightData[];
    commands?: Record<string, any>[];
}

export interface UserIntent {
    intent: IntentType;
    confidence: number;
    entities?: Record<string, any>;
    parameters?: Record<string, any>;
    visualizationType?: string;
    columns?: string[];
    queryType?: string;
}

// Phần insights và visualization
export interface InsightData {
    id?: string;
    fileId?: string;
    type: string;
    title: string;
    content: string;
    importance: number;
    columns?: string[];
    relatedCharts?: string[]; // Thống nhất naming (related_charts -> relatedCharts)
    metadata?: Record<string, any>;
}

export interface VisualizationData {
    id?: string;
    fileId?: string;
    type: string;
    title: string;
    description?: string;
    data: any[];
    config?: Record<string, any>;
    insight?: string;
    recommendedType?: string;
    relatedInsights?: string[];
    isCustom?: boolean;
}

// Chi tiết của DataQuality mới
export interface DataQualityMetrics {
    completeness: {
        score: number;
        missingCells: number;
        missingPercent: number;
        columnsWithMissing: string[];
        problematicColumns: string[];
    };
    consistency: {
        score: number;
        inconsistencyCount: number;
        inconsistentColumns: {
            column: string;
            issue: string;
        }[];
    };
    uniqueness: {
        score: number;
        duplicateRows: number;
        duplicatePercent: number;
        uniquenessStats: {
            column: string;
            uniqueValues: number;
            uniquePercent: number;
        }[];
        potentialIdentifiers: string[];
    };
    integrity: {
        score: number;
        integrityIssues: {
            column: string;
            issue: string;
        }[];
        outlierStats: Record<string, {
            outlierCount: number;
            outlierPercent: number;
        }>;
        rangeViolations: any[];
        dateViolations: {
            column: string;
            issue: string;
            details: Record<string, any>;
        }[];
    };
    accuracy: {
        score: number;
        accuracyIssues: {
            column: string;
            issue: string;
        }[];
        suspectColumns: string[];
    };
    overallScore: number;
}

// Phân tích file
export interface FileAnalysisResult {
    datasetInfo: {
        rows: number;
        columns: number;
        memoryUsageMb: number;
        dtypesSummary: Record<string, number>;
        columnTypes: {
            id: string[];
            numeric: string[];
            categorical: string[];
            datetime: string[];
            boolean: string[];
        };
        timeRange: string | null;
        missingValues: {
            count: number;
            percent: number;
        };
    };
    dataQuality: {
        qualityMetrics: DataQualityMetrics;
        issues: string[];
        recommendations: string[];
    };
    statisticalAnalysis: Record<string, any>;
    advancedAnalysis: Record<string, any>;
    insights: InsightData[];
    visualizations: VisualizationData[];
    recommendations: string[];
    performanceMetrics: Record<string, any>;
    timeSeriesAnalysis: Record<string, any>;
}

// Các interface tương tự hiện có
export interface ColumnStats {
    name: string;
    type: string;
    count: number;
    missing: number;
    unique: number;
    min?: number | string | Date;
    max?: number | string | Date;
    mean?: number;
    median?: number;
    stdDev?: number;
    distribution?: Record<string, number>;
}

export interface PredictionConfig {
    targetColumn: string;
    featureColumns: string[];
    modelType: string;
    timeColumn?: string;
    horizons?: number;
    testSize?: number;
    parameters?: Record<string, any>;
}

export interface PredictionResult {
    predictions: Record<string, any>[];
    metrics: Record<string, number>;
    modelInfo: Record<string, any>;
    importance?: Record<string, number>;
    visualization?: VisualizationData;
}

export interface MLServiceRequest {
    fileId?: string;
    userId?: string;
    data?: any;
}

export interface StreamEvent {
    event: string;
    id?: string;
    data: Record<string, any>;
}

// Thêm các interfaces còn thiếu
export interface TimeSeriesAnalysisRequest {
    dateColumn: string;
    valueColumn: string;
    forecast?: boolean;
    forecastPeriods?: number;
    exogenousVariables?: string[];
    returnConfidence?: boolean;
}

export interface CorrelationAnalysisRequest {
    columns?: string[];
    threshold?: number;
}

export interface ChartRecommendationRequest {
    columns?: string[];
    topK?: number;
}

export interface CreateChartRequest {
    chartType: string;
    columns: string[];
}

// Định nghĩa rõ ràng cho UploadResponse
export interface UploadResponse extends ApiResponse {
    data: {
        fileId: string;
        originalName: string;
        message: string;
    };
}

// Các interfaces cho Error
export interface ErrorDetail {
    code: string;
    message: string;
    location?: string;
    details?: Record<string, any>;
}

export interface ErrorResponse extends ApiResponse {
    status: ResponseStatus.ERROR;
    error: string;
    errorDetails?: ErrorDetail;
}

export interface SuccessResponse extends ApiResponse {
    status: ResponseStatus.SUCCESS;
    data: Record<string, any>;
}

export interface HealthResponse {
    status: string;
    version: string;
    uptime: number;
    checks: Record<string, Record<string, any>>;
}