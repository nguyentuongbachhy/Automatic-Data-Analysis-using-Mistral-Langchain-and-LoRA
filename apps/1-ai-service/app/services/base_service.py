# app/services/base_service.py
import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Union, Any, List

from app.models.analysis import InsightData

from ml.data.data_processor import DataProcessor
from ml.data.data_validator import DataValidator
from ml.analysis.analyzer import DataAnalyzer
from ml.visualization.charts import ChartGenerator
from ml.visualization.insights import InsightGenerator
from ml.visualization.recommender import ChartRecommender
from ml.analysis.time_series import TimeSeriesAnalyzer

logger = logging.getLogger(__name__)

class BaseService:
    """Base service class với các phương thức chung và hỗ trợ ML module"""
    
    def __init__(
        self, 
        config: Optional[Union[Dict, Any]] = None,
        cache: Optional[Any] = None,
        data_processor: Optional[DataProcessor] = None,
        data_validator: Optional[DataValidator] = None,
        data_analyzer: Optional[DataAnalyzer] = None
    ):
        """Khởi tạo base service"""
        self.config = config.config if hasattr(config, 'config') else config or {}
        self.cache = cache
        
        # Các components lazy-init
        self._data_processor = data_processor
        self._data_validator = data_validator
        self._data_analyzer = data_analyzer
        self._chart_generator = None
        self._insight_generator = None
        self._chart_recommender = None
        self._time_series_analyzer = None
        
    @property
    def data_processor(self) -> DataProcessor:
        """Lazy init DataProcessor từ ml/"""
        if self._data_processor is None:
            self._data_processor = DataProcessor(self.config)
        return self._data_processor
    
    @property
    def data_validator(self) -> DataValidator:
        """Lazy init DataValidator từ ml/"""
        if self._data_validator is None:
            self._data_validator = DataValidator(self.config)
        return self._data_validator
    
    @property
    def data_analyzer(self) -> DataAnalyzer:
        """Lazy init DataAnalyzer từ ml/"""
        if self._data_analyzer is None:
            self._data_analyzer = DataAnalyzer(self.config)
        return self._data_analyzer
    
    @property
    def chart_generator(self) -> ChartGenerator:
        """Lazy init ChartGenerator từ ml/"""
        if self._chart_generator is None:
            self._chart_generator = ChartGenerator(self.config)
        return self._chart_generator
    
    @property
    def insight_generator(self) -> InsightGenerator:
        """Lazy init InsightGenerator từ ml/"""
        if self._insight_generator is None:
            self._insight_generator = InsightGenerator(self.config)
        return self._insight_generator
    
    @property
    def chart_recommender(self) -> ChartRecommender:
        """Lazy init ChartRecommender từ ml/"""
        if self._chart_recommender is None:
            self._chart_recommender = ChartRecommender(self.config)
        return self._chart_recommender
    
    @property
    def time_series_analyzer(self) -> TimeSeriesAnalyzer:
        """Lazy init TimeSeriesAnalyzer từ ml/"""
        if self._time_series_analyzer is None:
            self._time_series_analyzer = TimeSeriesAnalyzer(self.config)
        return self._time_series_analyzer
    
    def _generate_cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """Tạo cache key từ prefix và parameters - Phương thức chung"""
        import hashlib
        import json
        
        # Chuyển thành JSON string để hash
        cache_str = json.dumps(params, sort_keys=True)
        return f"{prefix}-{hashlib.md5(cache_str.encode()).hexdigest()}"
    
    def detect_column_types(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Phát hiện kiểu cột sử dụng DataProcessor ML module"""
        try:
            return self.data_processor.get_column_types(df)
        except Exception as e:
            logger.error(f"Error detecting column types: {str(e)}")
            # Fallback dùng pandas builtin
            return self._basic_column_detection(df)
    
    def _basic_column_detection(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Fallback cho phát hiện cột khi ML module lỗi"""
        column_types = {
            "numeric": [],
            "categorical": [],
            "datetime": [],
            "text": [],
            "boolean": []
        }

        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                if set(df[col].dropna().unique()).issubset({0, 1, True, False}):
                    column_types["boolean"].append(col)
                else:
                    column_types["numeric"].append(col)
            
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                column_types["datetime"].append(col)
            
            elif pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                if df[col].nunique() < min(20, len(df) * 0.5):
                    column_types["categorical"].append(col)
                else:
                    column_types["text"].append(col)
            
            elif pd.api.types.is_bool_dtype(df[col]):
                column_types["boolean"].append(col)
        
        return column_types
        
    def preprocess_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tiền xử lý DataFrame sử dụng data_processor"""
        try:
            return self.data_processor.process(df)
        except Exception as e:
            logger.error(f"Error preprocessing DataFrame: {str(e)}")
            return df
            
    def generate_advanced_insights(self, df: pd.DataFrame, target_column: Optional[str] = None) -> List[InsightData]:
        """Tạo insights nâng cao dựa trên time series và advanced analytics"""
        insights = []
        try:
            # Phát hiện cột datetime
            datetime_cols = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
            
            # Nếu có cột datetime, chạy phân tích time series
            if datetime_cols and any(pd.api.types.is_numeric_dtype(df[col]) for col in df.columns):
                dt_col = datetime_cols[0]
                # Tìm cột numeric phù hợp
                target = target_column if target_column and pd.api.types.is_numeric_dtype(df[target_column]) else None
                
                if not target:
                    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
                    if numeric_cols:
                        target = numeric_cols[0]
                
                if target:
                    # Chạy phân tích time series
                    analysis = self.time_series_analyzer.analyze_time_series(df, dt_col, target)
                    
                    # Extract insights
                    if analysis.get("decomposition", {}).get("insight"):
                        insights.append(InsightData(
                            type = "time_series",
                            title = f"Time Series Analysis of {target}",
                            content= analysis["decomposition"]["insight"],
                            importance= 8,
                            columns= [dt_col, target]
                        ))
                        
                    if analysis.get("stationarity", {}).get("recommendation"):
                        insights.append(InsightData(
                            type = "time_series",
                            title = f"Stationarity Analysis",
                            content = analysis["stationarity"]["recommendation"],
                            importance = 7,
                            columns = [dt_col, target]
                        ))
                    
                    # Phát hiện changepoints
                    if analysis.get("changepoints", {}).get("insight"):
                        insights.append(InsightData(
                            type = "time_series",
                            title = "Change Points",
                            content = analysis["changepoints"]["insight"],
                            importance = 8,
                            columns = [dt_col, target]
                        ))
        except Exception as e:
            logger.error(f"Error generating advanced insights: {str(e)}")
            
        return insights
    
    def _convert_numpy_types(self, data):
        """Chuyển đổi tất cả các kiểu dữ liệu NumPy và Pandas thành Python native types"""
        import numpy as np
        import pandas as pd
        from datetime import datetime, date
        
        if data is None:
            return None
        
        if isinstance(data, pd.DataFrame):
            return data.to_dict(orient="records")
        
        elif isinstance(data, pd.Series):
            return data.tolist()
        
        elif isinstance(data, np.ndarray):
            return data.tolist()
        
        elif isinstance(data, np.integer):
            return int(data)
        elif isinstance(data, np.floating):
            return float(data)
        elif isinstance(data, np.bool_):
            return bool(data)
        
        elif isinstance(data, (datetime, date)):
            return data.isoformat()
        
        elif isinstance(data, set):
            return list(data)
        
        elif isinstance(data, dict):
            return {k: self._convert_numpy_types(v) for k, v in data.items()}
        
        elif isinstance(data, (list, tuple)):
            return [self._convert_numpy_types(item) for item in data]
        
        # Xử lý Pydantic models
        elif hasattr(data, 'model_dump'):
            return self._convert_numpy_types(data.model_dump())
        
        return data