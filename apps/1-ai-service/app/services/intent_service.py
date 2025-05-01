# app/services/intent_service.py
import logging
import re
from typing import Dict, List, Optional, Tuple
import pandas as pd
import textwrap

from app.core.config import ModelConfig
from app.models.chat import UserIntent, IntentType
from ml.model.mistral_inference import MistralInference
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)

class IntentDetectionService(BaseService):
    """Service phát hiện ý định người dùng, tích hợp với MLService"""
    _instance = None

    @classmethod
    def get_instance(cls, config: Optional[ModelConfig] = None, model: Optional[MistralInference] = None):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = IntentDetectionService(config=config, model=model)
        return cls._instance

    def __init__(self, config: Optional[Dict] = None, model: Optional[MistralInference] = None):
        """Khởi tạo service với tích hợp Mistral"""
        super().__init__(config=config)
        
        # Cấu hình intent detection từ config
        self.intent_config = self.config.get("inference", {}).get("intent_detection", {})
        self.rule_based_enabled = self.intent_config.get("use_rule_based", True)
        self.llm_fallback = self.intent_config.get("fallback_to_llm", True)
        self.confidence_threshold = self.intent_config.get("confidence_threshold", 0.7)
        
        # Tạo config cho MistralInference với LoRA
        if model:
            self.mistral = model
        else:
            # Đảm bảo config cho model có thông tin LoRA
            model_config = self.config.copy() if self.config else {}
            if "model" not in model_config:
                model_config["model"] = {}
                
            if "lora_config" not in model_config["model"]:
                model_config["model"]["lora_config"] = {"enabled": True}
                
            # Sử dụng intent adapter path nếu chưa được set
            if not model_config["model"].get("peft_model_path"):
                model_config["model"]["peft_model_path"] = self.intent_config.get(
                    "lora_adapter_path", "models/intent_detection_lora"
                )
                
            self.mistral = MistralInference(model_config)
        
        # Khởi tạo patterns
        self._init_patterns()
        
        logger.info("IntentDetectionService initialized with rule-based detection and ML fallback")
    
    def _init_patterns(self) -> None:
        """Khởi tạo các regex pattern cho rule-based detection"""
        self.patterns = {
            IntentType.QUESTION: [
                r"(what|what's|calculate|compute|find|tell me|show me).*(average|mean|median|sum|count|min|max)",
                r"how many.+\?",
                r"(what is|what's|what are|what percentage)",
                r"(why|when|where|who|which|how much|how long|how often)"
            ],
            IntentType.VISUALIZATION: [
                r"(visualize|plot|draw|show|display|create|make|generate).*(chart|graph|plot)",
                r"(bar chart|line chart|scatter plot|pie chart|histogram|heatmap|treemap)",
                r"(visualize|visualisation|visualization)",
                r"(show|display).*(data|trend|pattern|distribution)",
                r"(graph|chart|plot).*(data|trend|pattern|distribution)"
            ],
            IntentType.ANALYSIS: [
                r"(analyze|analyse|analysis|examine|study|investigate)",
                r"(compare|correlation|relationship|association)",
                r"(trend|pattern|fluctuation|variation|change over time)",
                r"(statistical|statistics|stats|descriptive analysis)"
            ],
            IntentType.INSIGHT: [
                r"(insight|key finding|important|significant|highlight)",
                r"(interesting|notable|remarkable|noteworthy)",
                r"(summarize|summary|overview|takeaway|key point)"
            ],
            IntentType.PREDICTION: [
                r"(predict|forecast|projection|estimation)",
                r"(will|future|expected|anticipated|projected)",
                r"(model|regression|classification|clustering|machine learning)"
            ]
        }

        self.chart_keywords = {
            "bar": ["bar", "column"],
            "line": ["line", "trend", "time series"],
            "scatter": ["scatter", "correlation", "relationship"],
            "pie": ["pie", "proportion", "distribution"],
            "histogram": ["histogram", "distribution", "frequency"],
            "heatmap": ["heat", "heatmap", "correlation", "matrix"]
        }
    
    async def detect_intent(
        self,
        query: str,
        df: Optional[pd.DataFrame] = None
    ) -> UserIntent:
        """
        Phát hiện intent từ query người dùng
        
        Args:
            query: Câu hỏi của người dùng
            message_history: Lịch sử tin nhắn trước đó (optional)
            df: DataFrame đang được phân tích (optional)
            
        Returns:
            UserIntent: Intent được phát hiện
        """
        try:
            # 1. Rule-based detection first (nhanh và ổn định)
            if self.rule_based_enabled:
                intent, confidence, viz_type, columns = self._rule_based_detection(query, df)
                
                # Nếu rule-based đủ tự tin, dùng kết quả
                if confidence >= self.confidence_threshold:
                    return UserIntent(
                        intent=intent,
                        confidence=confidence,
                        entities={},
                        parameters={},
                        visualization_type=viz_type,
                        columns=columns
                    )
            
            # 2. Fallback to LLM-based detection nếu cần
            if self.llm_fallback:
                llm_intent, llm_confidence, llm_viz_type, llm_columns = await self._llm_based_detection(query, df)
                
                return UserIntent(
                    intent=llm_intent,
                    confidence=llm_confidence,
                    entities={},
                    parameters={},
                    visualization_type=llm_viz_type,
                    columns=llm_columns
                )
            
            # 3. Nếu không fallback, trả về intent mặc định với confidence thấp
            return UserIntent(
                intent=IntentType.QUESTION,
                confidence=0.4,
                entities={},
                parameters={}
            )
        except Exception as e:
            logger.error(f"Error detecting intent: {str(e)}", exc_info=True)
            return UserIntent(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                entities={},
                parameters={}
            )
    
    def _rule_based_detection(
        self, query: str, df: Optional[pd.DataFrame] = None
    ) -> Tuple[IntentType, float, Optional[str], Optional[List[str]]]:
        """
        Phát hiện intent dựa trên rules và regex patterns
        
        Returns:
            Tuple: (intent_type, confidence, visualization_type, columns)
        """
        normalized_query = query.lower()
        
        # Tính intent scores cho các loại
        intent_scores = {}
        for intent_type, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, normalized_query):
                    score += 1
            intent_scores[intent_type] = score
        
        # Tìm intent có score cao nhất
        if max(intent_scores.values()) > 0:
            best_intent = max(intent_scores.items(), key=lambda x: x[1])[0]
            confidence = min(0.5 + 0.1 * intent_scores[best_intent], 0.95)
        else:
            best_intent = IntentType.QUESTION
            confidence = 0.4
        
        # Phát hiện columns nếu có DataFrame
        columns = []
        if df is not None:
            # Phát hiện columns được đề cập
            for col in df.columns:
                if col.lower() in normalized_query:
                    columns.append(col)
                    
            # Tìm columns phù hợp nếu không tìm thấy columns cụ thể
            if len(columns) == 0 and best_intent == IntentType.VISUALIZATION:
                columns = self._smart_column_selection(df, normalized_query)
                        
        # Phát hiện visualization type
        visualization_type = None
        if best_intent == IntentType.VISUALIZATION:
            for chart_type, keywords in self.chart_keywords.items():
                for keyword in keywords:
                    if keyword in normalized_query:
                        visualization_type = chart_type
                        break
                if visualization_type:
                    break
            
            # Sử dụng chart_recommender từ ML module nếu không có type cụ thể
            if not visualization_type and df is not None and columns:
                best_charts = self.chart_recommender.get_best_charts(df, columns, top_k=1)
                if best_charts and "chart_type" in best_charts[0]:
                    visualization_type = best_charts[0]["chart_type"]
        
        return best_intent, confidence, visualization_type, columns if columns else None
    
    async def _llm_based_detection(
        self,
        query: str,
        df: Optional[pd.DataFrame] = None
    ) -> Tuple[IntentType, float, Optional[str], Optional[List[str]]]:
        """
        Phát hiện intent sử dụng Mistral LLM
        
        Returns:
            Tuple: (intent_type, confidence, visualization_type, columns)
        """
        try:
            # Tạo prompt cho Mistral
            prompt = self._create_intent_prompt(query, df)
            
            # Thực hiện inference
            response = self.mistral.generate(
                prompt=prompt, 
                temperature=0.1,  # Thấp để đảm bảo ổn định
                max_tokens=300
            )
            
            # Parse kết quả
            intent, confidence, viz_type, columns = self._parse_llm_response(response, df)
            
            if hasattr(self.mistral.model_container.get("model", {}), "peft_config"):
                confidence = min(confidence + 0.1, 0.99)
        
            return intent, confidence, viz_type, columns
        
        except Exception as e:
            logger.error(f"Error in LLM-based intent detection: {str(e)}", exc_info=True)
            return IntentType.UNKNOWN, 0.0, None, None
    
    def _create_intent_prompt(
        self,
        query: str,
        df: Optional[pd.DataFrame] = None
    ) -> str:
        """Tạo prompt cho LLM intent detection với tối ưu hóa cho LoRA"""
        
        prompt = textwrap.dedent("""\
            You are an AI assistant that helps analyze user queries to determine their intent.
            Based on the provided query, identify the most likely user intent from the following options:
            - QUESTION: General questions about the data or requesting information
            - VISUALIZATION: Requests to visualize or plot data
            - ANALYSIS: Requests for analysis or insights about data
            - INSIGHT: Requests for key findings or important information
            - PREDICTION: Requests to predict future values or forecast trends

            User Query: "{query}"
        """)
        
        # Thêm thông tin về DataFrame nếu có
        if df is not None:
            df_info = textwrap.dedent(f"""\
                
                DataFrame Information:
                - Number of rows: {len(df)}
                - Number of columns: {len(df.columns)}
                - Column names: {', '.join(df.columns.tolist())}
            """)
            prompt += df_info
            column_types = self.detect_column_types(df)
            if column_types:
                numeric_cols = column_types.get("numeric", [])
                categorical_cols = column_types.get("categorical", [])
                datetime_cols = column_types.get("datetime", [])
                
                col_info = textwrap.dedent(f"""\
                    - Numeric columns: {', '.join(numeric_cols) if numeric_cols else 'None'}
                    - Categorical columns: {', '.join(categorical_cols) if categorical_cols else 'None'}
                    - Datetime columns: {', '.join(datetime_cols) if datetime_cols else 'None'}
                """)
                prompt += col_info
        
        ending = textwrap.dedent("""\
            
            Respond with ONLY a JSON object in the following format:
            {{
            "intent": "INTENT_TYPE", 
            "confidence": 0.95,
            "visualization_type": "bar|line|scatter|pie|histogram|heatmap|null",
            "columns": ["column1", "column2"]
            }}

            If the intent is VISUALIZATION, include the visualization_type and columns fields.
            If columns are not specified in the query, select the most appropriate columns from the dataframe.
        """)
        prompt += ending

        return prompt.format(query=query)
    
    def _parse_llm_response(
        self, 
        response: str, 
        df: Optional[pd.DataFrame] = None
    ) -> Tuple[IntentType, float, Optional[str], Optional[List[str]]]:
        import json
        import re
        
        # Default fallback values
        default_intent = IntentType.QUESTION
        default_confidence = 0.5
        
        try:
            # Try to extract JSON from the response
            json_matches = re.findall(r'\{[^{}]*\}', response)
            
            # If no JSON-like structure found, use fallback
            if not json_matches:
                logger.warning(f"No JSON structure found in response: {response}")
                return default_intent, default_confidence, None, None
            
            # Try parsing each potential JSON match
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    
                    # Validate required keys
                    if not all(key in data for key in ['intent']):
                        continue
                    
                    # Extract intent
                    intent_str = data.get("intent", "UNKNOWN").upper()
                    intent = getattr(IntentType, intent_str, IntentType.UNKNOWN)
                    
                    # Extract confidence
                    confidence = float(data.get("confidence", default_confidence))
                    
                    # Extract visualization type
                    viz_type = data.get("visualization_type")
                    
                    # Extract and validate columns
                    columns = data.get("columns", [])
                    if df is not None and columns:
                        valid_columns = [col for col in columns if col in df.columns]
                        columns = valid_columns if valid_columns else None
                    
                    return intent, confidence, viz_type, columns
                
                except json.JSONDecodeError:
                    # If this specific JSON match fails, continue to next
                    continue
            
            # If no valid JSON found
            logger.warning(f"No valid JSON parsed from response: {response}")
            return default_intent, default_confidence, None, None
        
        except Exception as e:
            logger.error(f"Unexpected error parsing LLM response: {str(e)}\nResponse: {response}", exc_info=True)
            return default_intent, default_confidence, None, None
    
    def _smart_column_selection(
        self, df: pd.DataFrame, query: str
    ) -> List[str]:
        """
        Chọn columns thông minh từ DataFrame dựa trên query và kiểu biểu đồ
        
        Returns:
            List[str]: Danh sách columns phù hợp
        """
        # Lấy 2 columns phù hợp nhất dựa trên chart recommender
        best_charts = self.chart_recommender.get_best_charts(df, None, top_k=1)
        
        if best_charts and "columns" in best_charts[0]:
            columns_str = best_charts[0]["columns"]
            if isinstance(columns_str, str) and " vs " in columns_str:
                return columns_str.split(" vs ")
            elif isinstance(columns_str, list):
                return columns_str
        if df is not None:
            column_types = self.detect_column_types(df)

        # Fallback: chọn cột phù hợp dựa trên kiểu dữ liệu
        numeric_cols = column_types["numeric"]
        datetime_cols = column_types["datetime"]
        categorical_cols = column_types["categorical"]
        # Phán đoán loại biểu đồ từ query
        is_time_series = any(term in query.lower() for term in 
                          ["time", "trend", "over time", "timeseries", "series"])
        
        is_correlation = any(term in query.lower() for term in 
                          ["correlation", "relationship", "compare", "versus", "vs"])
        
        is_distribution = any(term in query.lower() for term in 
                           ["distribution", "histogram", "frequency"])
        
        # Chọn cột phù hợp dựa trên loại biểu đồ
        if is_time_series and datetime_cols and numeric_cols:
            return [datetime_cols[0], numeric_cols[0]]
            
        elif is_correlation and len(numeric_cols) >= 2:
            return numeric_cols[:2]
            
        elif is_distribution and numeric_cols:
            return [numeric_cols[0]]
            
        elif categorical_cols and numeric_cols:
            return [categorical_cols[0], numeric_cols[0]]
            
        # Fallback cuối cùng
        columns = []
        if numeric_cols:
            columns.append(numeric_cols[0])
        if len(numeric_cols) > 1:
            columns.append(numeric_cols[1])
        elif datetime_cols:
            columns.append(datetime_cols[0])
        elif categorical_cols:
            columns.append(categorical_cols[0])
            
        return columns