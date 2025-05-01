import { z } from 'zod';

// Updated Enum schemas
const ResponseStatusSchema = z.enum(['success', 'error', 'pending']);
const InsightTypeSchema = z.enum([
    'correlation', 'trend', 'distribution', 'outlier',
    'summary', 'pattern', 'anomaly', 'comparison',
    'likert', 'binary', 'gender', 'range', 'text'
]);
const ChartTypeSchema = z.enum([
    'line', 'bar', 'scatter', 'pie', 'histogram', 'grouped histogram',
    'box', 'heatmap', 'area', 'bubble', 'radar', 'combo',
    'waterfall', 'treemap', 'sankey', 'likert', 'word cloud',
    'range', 'text', 'likert correlation', 'bar grouped', 'violin',
    'mosaic', 'scatter 3d', 'chord', 'facet', 'gantt', 'donut',
    'hexbin', 'network', 'animation', 'diverging', 'matrix', 'regression'
]);
const MessageRoleSchema = z.enum(['system', 'user', 'assistant']);
const IntentTypeSchema = z.enum([
    'question', 'visualization', 'analysis',
    'insight', 'prediction', 'unknown'
]);

// Base schemas
export const ApiResponseSchema = z.object({
    status: ResponseStatusSchema,
    data: z.record(z.any()).nullable().optional(),
    error: z.string().nullable().optional(),
    meta: z.record(z.any()).optional()
});

export const PaginatedResponseSchema = ApiResponseSchema.extend({
    page: z.number(),
    pageSize: z.number(),
    total: z.number(),
    totalPages: z.number()
});

// Updated Chat schemas
export const ChatMessageSchema = z.object({
    role: MessageRoleSchema,
    content: z.string()
});

export const ChatRequestSchema = z.object({
    query: z.string(),
    userId: z.string().optional(),
    fileId: z.string().optional(),
    chatId: z.string().optional(),
    useCache: z.boolean().optional()
});

// Updated Insight schema - importance is now float
export const InsightSchema = z.object({
    id: z.string().optional(),
    fileId: z.string().optional(),
    type: z.string(), // Using string for flexibility
    title: z.string(),
    content: z.string(),
    importance: z.number(), // Changed to number from int
    columns: z.array(z.string()).optional(),
    relatedCharts: z.array(z.string()).optional(),
    metadata: z.record(z.any()).optional()
});

export const VisualizationSchema = z.object({
    id: z.string().optional(),
    fileId: z.string().optional(),
    type: z.string(), // Using string for flexibility
    title: z.string(),
    description: z.string().optional(),
    data: z.array(z.record(z.any())),
    config: z.record(z.any()).optional(),
    insight: z.string().optional(),
    recommendedType: z.string().nullable().optional(),
    relatedInsights: z.array(z.string()).optional(),
    isCustom: z.boolean().optional()
});

export const ChatResponseSchema = z.object({
    response: z.string(),
    visualizations: z.array(VisualizationSchema).optional(),
    insights: z.array(InsightSchema).optional(),
    commands: z.array(z.record(z.any())).optional()
});

export const UserIntentSchema = z.object({
    intent: IntentTypeSchema,
    confidence: z.number(),
    entities: z.record(z.any()).optional(),
    parameters: z.record(z.any()).optional(),
    visualizationType: z.string().optional(),
    columns: z.array(z.string()).optional(),
    queryType: z.string().optional()
});

// Data quality schemas
export const DataQualityMetricsSchema = z.object({
    completeness: z.object({
        score: z.number(),
        missingCells: z.number(),
        missingPercent: z.number(),
        columnsWithMissing: z.array(z.string()),
        problematicColumns: z.array(z.string())
    }),
    consistency: z.object({
        score: z.number(),
        inconsistencyCount: z.number(),
        inconsistentColumns: z.array(z.object({
            column: z.string(),
            issue: z.string()
        }))
    }),
    uniqueness: z.object({
        score: z.number(),
        duplicateRows: z.number(),
        duplicatePercent: z.number(),
        uniquenessStats: z.array(z.object({
            column: z.string(),
            uniqueValues: z.number(),
            uniquePercent: z.number()
        })),
        potentialIdentifiers: z.array(z.string())
    }),
    integrity: z.object({
        score: z.number(),
        integrityIssues: z.array(z.object({
            column: z.string(),
            issue: z.string()
        })),
        outlierStats: z.record(z.object({
            outlierCount: z.number(),
            outlierPercent: z.number()
        })),
        rangeViolations: z.array(z.any()),
        dateViolations: z.array(z.object({
            column: z.string(),
            issue: z.string(),
            details: z.record(z.any())
        }))
    }),
    accuracy: z.object({
        score: z.number(),
        accuracyIssues: z.array(z.object({
            column: z.string(),
            issue: z.string()
        })),
        suspectColumns: z.array(z.string())
    }),
    overallScore: z.number()
});

// Update column types to include new chart and insight types
export const FileAnalysisResultSchema = z.object({
    datasetInfo: z.object({
        rows: z.number(),
        columns: z.number(),
        memoryUsageMb: z.number(),
        dtypesSummary: z.record(z.number()),
        columnTypes: z.object({
            id: z.array(z.string()),
            numeric: z.array(z.string()),
            categorical: z.array(z.string()),
            datetime: z.array(z.string()),
            boolean: z.array(z.string()),
            // Add optional new column types
            likert: z.array(z.string()).optional(),
            gender: z.array(z.string()).optional(),
            range: z.array(z.string()).optional(),
            text: z.array(z.string()).optional(),
            binary: z.array(z.string()).optional(),
            email: z.array(z.string()).optional(),
            phone: z.array(z.string()).optional(),
            address: z.array(z.string()).optional(),
            name: z.array(z.string()).optional(),
            url: z.array(z.string()).optional()
        }),
        timeRange: z.string().nullable(),
        missingValues: z.object({
            count: z.number(),
            percent: z.number()
        })
    }),
    dataQuality: z.object({
        qualityMetrics: DataQualityMetricsSchema,
        issues: z.array(z.string()),
        recommendations: z.array(z.string())
    }),
    statisticalAnalysis: z.record(z.any()),
    advancedAnalysis: z.record(z.any()),
    insights: z.array(InsightSchema),
    visualizations: z.array(VisualizationSchema),
    recommendations: z.array(z.string()),
    performanceMetrics: z.record(z.any()),
    timeSeriesAnalysis: z.record(z.any())
});

export const ColumnStatsSchema = z.object({
    name: z.string(),
    type: z.string(),
    count: z.number(),
    missing: z.number(),
    unique: z.number(),
    min: z.union([z.number(), z.string(), z.date()]).optional(),
    max: z.union([z.number(), z.string(), z.date()]).optional(),
    mean: z.number().optional(),
    median: z.number().optional(),
    stdDev: z.number().optional(),
    distribution: z.record(z.number()).optional()
});

// Prediction related schemas
export const PredictionConfigSchema = z.object({
    targetColumn: z.string(),
    featureColumns: z.array(z.string()),
    modelType: z.string(),
    timeColumn: z.string().optional(),
    horizons: z.number().optional(),
    testSize: z.number().optional(),
    parameters: z.record(z.any()).optional()
});

export const PredictionResultSchema = z.object({
    predictions: z.array(z.record(z.any())),
    metrics: z.record(z.number()),
    modelInfo: z.record(z.any()),
    importance: z.record(z.number()).optional(),
    visualization: VisualizationSchema.optional()
});

// Request schemas - UPDATED: removed filePath requirement
export const MLServiceRequestSchema = z.object({
    fileId: z.string(), // Changed to required
    userId: z.string(), // Changed to required
    data: z.any().optional(),
    useCache: z.boolean().optional()
});

export const TimeSeriesAnalysisRequestSchema = z.object({
    dateColumn: z.string(),
    valueColumn: z.string(),
    forecast: z.boolean().optional(),
    forecastPeriods: z.number().optional(),
    exogenousVariables: z.array(z.string()).optional(),
    returnConfidence: z.boolean().optional()
});

export const CorrelationAnalysisRequestSchema = z.object({
    fileId: z.string(), // Required
    columns: z.array(z.string()).optional(),
    threshold: z.number().optional()
});

export const ChartRecommendationRequestSchema = z.object({
    fileId: z.string(), // Required
    columns: z.array(z.string()).optional(),
    topK: z.number().optional()
});

export const CreateChartRequestSchema = z.object({
    fileId: z.string(), // Required
    chartType: z.string(),
    columns: z.array(z.string()),
    title: z.string().optional(),
    description: z.string().optional()
});

// Error schemas
export const ErrorDetailSchema = z.object({
    code: z.string(),
    message: z.string(),
    location: z.string().optional(),
    details: z.record(z.any()).optional()
});

export const ErrorResponseSchema = ApiResponseSchema.extend({
    status: z.literal(ResponseStatusSchema.enum.error),
    error: z.string(),
    errorDetails: ErrorDetailSchema.optional()
});

export const SuccessResponseSchema = ApiResponseSchema.extend({
    status: z.literal(ResponseStatusSchema.enum.success),
    data: z.record(z.any())
});

// Upload and health schemas
export const UploadResponseSchema = ApiResponseSchema.extend({
    data: z.object({
        fileId: z.string(),
        originalName: z.string(),
        message: z.string()
    })
});

export const HealthResponseSchema = z.object({
    status: z.string(),
    version: z.string(),
    uptime: z.number(),
    checks: z.record(z.record(z.any()))
});