from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class InsightType(str, Enum):
    """Các loại insights"""
    CORRELATION = "correlation"
    TREND = "trend"
    DISTRIBUTION = "distribution"
    OUTLIER = "outlier"
    SUMMARY = "summary"
    PATTERN = "pattern"
    ANOMALY = "anomaly"
    COMPARISON = "comparison"
    LIKERT = "likert"
    BINARY = "binary"
    GENDER = "gender"
    RANGE = "range"
    TEXT = "text"

class ChartType(str, Enum):
    """Các loại biểu đồ"""
    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"
    PIE = "pie"
    HISTOGRAM = "histogram"
    GROUPED_HISTOGRAM = "grouped histogram"
    BOX = "box"
    HEATMAP = "heatmap"
    AREA = "area"
    BUBBLE = "bubble"
    RADAR = "radar"
    COMBO = "combo"
    WATERFALL = "waterfall"
    TREEMAP = "treemap"
    SANKEY = "sankey"
    LIKERT = "likert"
    WORD_CLOUD = "word cloud"
    RANGE = "range"
    TEXT = "text"
    LIKERT_CORRELATION = "likert correlation"
    
    # Các loại biểu đồ bổ sung
    BAR_GROUPED = "bar grouped"
    VIOLIN = "violin"
    MOSAIC = "mosaic"
    SCATTER_3D = "scatter 3d"
    CHORD = "chord"
    FACET = "facet"
    GANTT = "gantt"
    DONUT = "donut"
    HEXBIN = "hexbin"
    NETWORK = "network"
    ANIMATION = "animation"
    DIVERGING = "diverging"
    MATRIX = "matrix"
    REGRESSION = "regression"


class InsightData(BaseModel):
    """Định dạng insight data"""
    id: Optional[str] = None
    fileId: Optional[str] = None
    type: str
    title: str
    content: str
    importance: float
    columns: Optional[List[str]] = []
    related_charts: Optional[List[str]] = []
    metadata: Optional[Dict[str, Any]] = {}

class VisualizationData(BaseModel):
    """Định dạng data biểu đồ"""
    id: Optional[str] = None
    fileId: Optional[str] = None
    type: str
    title: str
    description: Optional[str] = None
    data: List[Dict[str, Any]]
    config: Optional[Dict[str, Any]] = None
    insight: Optional[str] = None
    recommendedType: Optional[str] = None
    relatedInsights: Optional[List[str]] = []
    isCustom: bool = False


class PredictionConfig(BaseModel):
    """Cấu hình cho việc dự đoán"""
    targetColumn: str
    featureColumns: List[str]
    modelType: str  # regression, classification, time_series, etc.
    timeColumn: Optional[str] = None
    horizons: Optional[int] = None  # Số kỳ dự báo cho time series
    testSize: float = 0.2
    parameters: Optional[Dict[str, Any]] = None


class PredictionResult(BaseModel):
    """Kết quả dự đoán"""
    predictions: List[Dict[str, Any]]
    metrics: Dict[str, float]
    modelInfo: Dict[str, Any]
    importance: Optional[Dict[str, float]] = None
    visualization: Optional[VisualizationData] = None