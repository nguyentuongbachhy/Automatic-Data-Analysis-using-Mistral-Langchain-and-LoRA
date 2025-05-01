from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from app.models.analysis import VisualizationData, InsightData


class MessageRole(str, Enum):
    """Vai trò của tin nhắn"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class ChatRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    chat_id: Optional[str] = None
    file_id: Optional[str] = None
    use_cache: bool = False

class ChatResponse(BaseModel):
    """Định dạng response từ chat API"""
    response: str
    visualizations: Optional[List[VisualizationData]] = None
    insights: Optional[List[InsightData]] = None
    commands: Optional[List[Dict[str, Any]]] = None


class StreamEvent(BaseModel):
    """Mô hình event stream"""
    event: str
    id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class IntentType(str, Enum):
    """Loại intent của người dùng"""
    QUESTION = "question"
    VISUALIZATION = "visualization"
    ANALYSIS = "analysis"
    INSIGHT = "insight"
    PREDICTION = "prediction"
    UNKNOWN = "unknown"


class UserIntent(BaseModel):
    """Mô hình intent của người dùng"""
    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    entities: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    visualization_type: Optional[str] = None
    columns: Optional[List[str]] = None
    query_type: Optional[str] = None