// Import enums from common.ts
import {
    ChartType,
    InsightType,
    IntentType,
    MessageRole,
    ResponseStatus
} from './common';

// Export all enums
export * from './common';

// =============================================================
// API Response Interfaces
// =============================================================

/**
 * Standard API response interface
 */
export interface ApiResponse<T = any> {
    status: ResponseStatus;
    data?: T | null;
    error?: string | null;
    meta?: Record<string, any>;
}

/**
 * Paginated API response interface
 */
export interface PaginatedResponse<T = any> extends ApiResponse<T> {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
}

/**
 * Error detail information
 */
export interface ErrorDetail {
    code: string;
    message: string;
    location?: string;
    details?: Record<string, any>;
}

/**
 * Enhanced error response
 */
export interface ErrorResponse extends ApiResponse {
    status: ResponseStatus.ERROR;
    error: string;
    errorDetails?: ErrorDetail;
}

/**
 * Success response type
 */
export interface SuccessResponse extends ApiResponse {
    status: ResponseStatus.SUCCESS;
    data: Record<string, any>;
}

/**
 * Health check response
 */
export interface HealthResponse {
    status: string;
    version: string;
    uptime: number;
    checks: Record<string, Record<string, any>>;
}

// =============================================================
// Authentication Interfaces
// =============================================================

/**
 * User interface representing a system user
 */
export interface User {
    id: string;
    email: string;
    name?: string;
    createdAt?: string;
    updatedAt?: string;
}

/**
 * Authentication state for the application
 */
export interface AuthState {
    isAuthenticated: boolean;
    user: User | null;
    token: string | null;
    loading: boolean;
    error: string | null;
}

/**
 * Login credentials for authentication
 */
export interface LoginCredentials {
    email: string;
    password: string;
}

/**
 * Registration data for new accounts
 */
export interface RegisterData {
    name: string;
    email: string;
    password: string;
    confirmPassword?: string;
}

/**
 * Auth response from the server
 */
export interface AuthResponse {
    token: string;
    user: User;
}

// =============================================================
// Chat and Conversation Interfaces
// =============================================================

/**
 * Basic chat message
 */
export interface ChatMessage {
    role: MessageRole;
    content: string;
}

/**
 * Enhanced message with metadata
 */
export interface Message {
    id: string;
    chatId: string;
    role: MessageRole;
    content: string;
    metadata?: Record<string, any> | null;
    createdAt: string;
    updatedAt: string;
}

/**
 * Chat request parameters
 */
export interface ChatRequest {
    query: string;
    userId: string;
    chatId: string;
    fileId?: string;
    useCache?: boolean;
}

/**
 * Response from chat API
 */
export interface ChatResponse {
    id: string;
    response: string;
    visualizations?: VisualizationData[];
    insights?: InsightData[];
    commands?: Record<string, any>[];
}

/**
 * Complete chat conversation data
 */
export interface ChatData {
    id: string;
    userId: string;
    fileId?: string;
    title: string;
    createdAt: string;
    updatedAt: string;
    messages: Message[];
}

/**
 * User intent detection result
 */
export interface UserIntent {
    intent: IntentType;
    confidence: number;
    entities?: Record<string, any>;
    parameters?: Record<string, any>;
    visualizationType?: string;
    columns?: string[];
    queryType?: string;
}

// =============================================================
// Chart and Visualization Interfaces
// =============================================================

/**
 * Data structure for chart visualizations
 */

export interface CorrelationData {
    visualization?: any;
    strongCorrelations?: Array<{
        column1: string;
        column2: string;
        correlation: number;
    }>;
    insights?: Array<{
        title: string;
        content: string;
    }>;
}

export interface TimeSeriesData {
    visualization?: {
        data: any[];
        description?: string;
    };
    timeSeriesInfo?: {
        dataPoints?: number;
        startDate?: string;
        endDate?: string;
        frequency?: string;
        hasTrend?: boolean;
        hasSeasonality?: boolean;
    };
    forecast?: {
        horizon?: number;
        forecastData?: Array<{
            date: string;
            value: number;
            lower?: number;
            upper?: number;
        }>;
        predictionIntervals?: boolean;
    };
    metrics?: Record<string, number>;
    insights?: string[];
}

export interface RecommendedChartData {
    columns: string[];
    chartType: string;
    score: number;
    description: string;
    title: string;
    columnTypes: string[];
    fileId?: string;
    category?: string;
    subcategory?: string;
    complexity?: string;
}

export interface VisualizationData {
    id?: string;
    fileId?: string;
    type: ChartType | string;
    title: string;
    description?: string;
    data: any[];
    config?: Record<string, any>;
    parameters?: Record<string, any>;
    chartLibrary?: string;
    insight?: string;
    recommendedType?: string | null;
    relatedInsights?: string[];
    isCustom?: boolean;
    createdAt?: string;
    updatedAt?: string;
}

/**
 * Chart recommendation
 */
export interface ChartRecommendation {
    bestCharts?: RecommendedChartData[];
    createdAt?: string;
    updatedAt?: string;
}

/**
 * Data insight information
 */
export interface InsightData {
    id?: string;
    fileId?: string;
    type: InsightType | string;
    title: string;
    content: string;
    importance: number;
    sourceType?: string;
    columns?: string[];
    relatedCharts?: string[];
    metadata?: Record<string, any> | null;
    createdAt?: string;
    updatedAt?: string;
}

// =============================================================
// Data Analysis Interfaces
// =============================================================

/**
 * Information about a column in a file
 */
export interface ColumnInfo {
    id?: string;
    fileId?: string;
    name: string;
    displayName?: string;
    type: string;
    stats: Record<string, any>;
    quality?: number;
    completeness?: number;
    nullable?: boolean;
    createdAt?: string;
    updatedAt?: string;
}

/**
 * Statistical information about a column
 */
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

/**
 * Data quality metrics
 */
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

/**
 * File analysis data
 */
export interface Analysis {
    id: string;
    fileId: string;
    rowCount: number;
    columnCount: number;
    missingValues: number;
    duplicateRows: number;
    outliers: number;

    datasetInfo?: Record<string, any> | null;
    statisticalAnalysis?: Record<string, any> | null;
    advancedAnalysis?: Record<string, any> | null;

    qualityMetrics?: Record<string, any> | null;
    summary: Record<string, any>;
    dataQuality?: Record<string, any> | null;
    recommendations?: Record<string, any> | null;

    createdAt: string;
    updatedAt: string;
}

/**
 * Comprehensive file analysis result
 */
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

/**
 * Information about a file
 */
export interface FileData {
    id: string;
    filename: string;
    originalName: string;
    type: string;
    size: number;
    path: string;
    userId: string;
    qualityScore?: number;
    createdAt: string;
    updatedAt: string;

    // Related entities
    analysis?: Analysis;
    columns?: ColumnInfo[];
    insights?: InsightData[];
    visualizations?: VisualizationData[];
    predictions?: PredictionData[];
    timeSeriesAnalyses?: TimeSeriesAnalysis[];
    chartRecommendations?: ChartRecommendation[];

    // UI state properties
    isPending?: boolean;
    message?: string;
}

/**
 * Response for file upload
 */
export interface UploadResponse extends ApiResponse {
    data: {
        fileId: string;
        originalName: string;
        message: string;
    };
}

// =============================================================
// Prediction Interfaces
// =============================================================

/**
 * Configuration for prediction models
 */
export interface PredictionConfig {
    targetColumn: string;
    featureColumns: string[];
    modelType: string;
    timeColumn?: string;
    horizons?: number;
    testSize?: number;
    parameters?: Record<string, any>;
}

/**
 * Result of prediction operations
 */
export interface PredictionResult {
    predictions: Record<string, any>[];
    metrics: Record<string, number>;
    modelInfo: Record<string, any>;
    importance?: Record<string, number>;
    visualization?: VisualizationData;
}

/**
 * Prediction data
 */
export interface PredictionData {
    id: string;
    fileId: string;
    targetColumn: string;
    featureColumns: string[];
    modelType: string;
    config: Record<string, any>;
    results: Record<string, any>;
    metrics: Record<string, any>;
    testSize?: number;
    importance?: Record<string, any>;
    visualization?: Record<string, any>;
    createdAt: string;
    updatedAt: string;
}

/**
 * Prediction request parameters
 */
export interface PredictionRequest {
    fileId: string;
    filePath?: string;
    config: PredictionConfig;
}

// =============================================================
// Time Series Analysis Interfaces
// =============================================================

/**
 * Time series analysis data
 */
export interface TimeSeriesAnalysis {
    id: string;
    fileId: string;
    dateColumn: string;
    valueColumn: string;
    results: Record<string, any>;
    forecastIncluded: boolean;
    forecastPeriods?: number;
    createdAt: string;
    updatedAt: string;
}

/**
 * Parameters for time series analysis
 */
export interface TimeSeriesAnalysisRequest {
    dateColumn: string;
    valueColumn: string;
    forecast?: boolean;
    forecastPeriods?: number;
    exogenousVariables?: string[];
    returnConfidence?: boolean;
}

/**
 * Configuration for time series analysis
 */
export interface TimeSeriesAnalysisConfig {
    dateColumn: string;
    valueColumn: string;
    forecast?: boolean;
    forecastPeriods?: number;
    exogenousVariables?: string[];
    returnConfidence?: boolean;
}

// =============================================================
// Other Request Interfaces
// =============================================================

/**
 * Parameters for correlation analysis
 */
export interface CorrelationAnalysisRequest {
    columns?: string[];
    threshold?: number;
}

/**
 * Parameters for chart recommendation
 */
export interface ChartRecommendationRequest {
    columns?: string[];
    topK?: number;
}

/**
 * Parameters for creating a chart
 */
export interface CreateChartRequest {
    chartType: string;
    columns: string[];
}

/**
 * Global request interface for ML service
 */
export interface MLServiceRequest {
    fileId?: string;
    userId?: string;
    data?: any
}

// =============================================================
// Utility Functions
// =============================================================

/**
 * Convert snake_case to camelCase
 */
export function toCamelCase(str: string): string {
    return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Convert camelCase to snake_case
 */
export function toSnakeCase(str: string): string {
    return str.replace(/([A-Z])/g, '_$1').toLowerCase();
}

/**
 * Deep convert object keys from snake_case to camelCase
 */
export function deepCamelCaseKeys(obj: any): any {
    if (Array.isArray(obj)) {
        return obj.map(deepCamelCaseKeys);
    } else if (obj !== null && typeof obj === 'object') {
        return Object.keys(obj).reduce((result, key) => {
            const camelKey = toCamelCase(key);
            result[camelKey] = deepCamelCaseKeys(obj[key]);
            return result;
        }, {} as Record<string, any>);
    }
    return obj;
}

/**
 * Deep convert object keys from camelCase to snake_case
 */
export function deepSnakeCaseKeys(obj: any): any {
    if (Array.isArray(obj)) {
        return obj.map(deepSnakeCaseKeys);
    } else if (obj !== null && typeof obj === 'object') {
        return Object.keys(obj).reduce((result, key) => {
            const snakeKey = toSnakeCase(key);
            result[snakeKey] = deepSnakeCaseKeys(obj[key]);
            return result;
        }, {} as Record<string, any>);
    }
    return obj;
}

/**
 * Format file size in human-readable format
 */
export function formatFileSize(size: number): string {
    if (size < 1024) {
        return `${size} B`;
    } else if (size < 1024 * 1024) {
        return `${(size / 1024).toFixed(2)} KB`;
    } else {
        return `${(size / (1024 * 1024)).toFixed(2)} MB`;
    }
}