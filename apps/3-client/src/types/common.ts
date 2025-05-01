/**
 * Status of API responses
 */
export enum ResponseStatus {
    SUCCESS = "success",
    ERROR = "error",
    PENDING = "pending"
}

/**
 * Types of insights that can be generated
 */
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

/**
 * Types of charts that can be generated
 */
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
    SANKEY = "sankey",
    LIKERT = "likert",
    WORD_CLOUD = "word cloud",
    RANGE = "range",
    TEXT = "text",
    LIKERT_CORRELATION = "likert correlation",
    BAR_GROUPED = "bar grouped",
    VIOLIN = "violin",
    MOSAIC = "mosaic",
    SCATTER_3D = "scatter 3d",
    CHORD = "chord",
    FACET = "facet",
    GANTT = "gantt",
    DONUT = "donut",
    HEXBIN = "hexbin",
    NETWORK = "network",
    ANIMATION = "animation",
    DIVERGING = "diverging",
    MATRIX = "matrix",
    REGRESSION = "regression"
}

/**
 * Message roles in chat conversations
 */
export enum MessageRole {
    SYSTEM = "system",
    USER = "user",
    ASSISTANT = "assistant"
}

/**
 * Types of user intents that can be detected
 */
export enum IntentType {
    QUESTION = "question",
    VISUALIZATION = "visualization",
    ANALYSIS = "analysis",
    INSIGHT = "insight",
    PREDICTION = "prediction",
    UNKNOWN = "unknown"
}