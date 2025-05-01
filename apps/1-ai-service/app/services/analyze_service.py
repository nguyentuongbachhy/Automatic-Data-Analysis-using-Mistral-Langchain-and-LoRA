# app/services/analyze_service.py
import logging
import os
import math
import asyncio
import concurrent.futures
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4 as v4

import pandas as pd

from app.core.cache import InferenceCache
from app.services.model_service import ModelService
from app.services.intent_service import IntentDetectionService
from app.services.validation_service import ValidationService
from app.services.base_service import BaseService

from app.models.analysis import (
    ChartType, InsightData, PredictionConfig,
    PredictionResult, VisualizationData
)
from app.models.chat import IntentType

from ml.utils.memory_utils import estimate_dataframe_size, optimize_dataframe_memory, chunk_dataframe
from ml.tools.postgres_connector import PostgreSQLConnector

logger = logging.getLogger(__name__)

class AnalyzeService(BaseService):
    """Analyze service với các cải tiến tận dụng kiến trúc ML"""

    def __init__(
        self,
        file_id: str,
        user_id: str,
        model_service: Optional[ModelService] = None,
        intent_service: Optional[IntentDetectionService] = None,
        validation_service: Optional[ValidationService] = None,
        config: Optional[Dict] = None,
        max_workers: int = 4
    ):
        """Khởi tạo service với tích hợp nhiều dịch vụ khác"""
        super().__init__(config=config)
        self.file_id = file_id
        self.user_id = user_id
        self.file_path = None
        self.model_service = model_service
        self.intent_service = intent_service
        self.validation_service = validation_service
        self.max_workers = max_workers
        self.connect = PostgreSQLConnector()

        # Cache với TTL phù hợp
        cache_config = self.config.get("cache", {})
        cache_ttl = cache_config.get("ttl_seconds", 3600)
        self.inference_cache = InferenceCache(ttl_seconds=cache_ttl)
        
        # Data processing config
        self.data_config = self.config.get("data_processing", {})
        self.max_rows_preview = self.data_config.get("max_rows_preview", 100)
        self.max_rows_analysis = self.data_config.get("max_rows_analysis", 100000)
        
        logger.info(f"AnalyzeService initialized for file_id={file_id}")

    def get_file_path(self,file_id: str, user_id: str) -> str:
        """
        Get path with file_id and user_id

        Args:
            file_id: ID of file
            user_id: ID of user
        """
        try:
            logger.info(f"Getting path for file_id={file_id}, user_id={user_id}")

            results = self.connect.select('File',columns={"path"}, conditions={
                "id": file_id,
                "userId": user_id
            })

            logger.info(f"Query result: {results}")

            if results and isinstance(results, list):
                return results[0]["path"]
            return None
        except Exception as e:
            logger.error(f"Error getting path with file_id={file_id} user_id={user_id}: {str(e)}", exc_info=e)
            return None

    async def load_and_validate_data(
        self, 
        sample: bool = False, 
        max_rows: Optional[int] = None
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Tải và xác thực dữ liệu từ file_path
        
        Args:
            sample: Có lấy mẫu không
            max_rows: Số lượng dòng tối đa
            
        Returns:
            Tuple[pd.DataFrame, Dict]: DataFrame và quality report
        """
        try:
            if not self.validation_service:
                raise ValueError("ValidationService is required but not provided")
            
            if not hasattr(self, 'file_path') or not self.file_path:
                # Lấy từ user_id trong context hoặc từ tham số
                # Điều này tùy thuộc vào cách bạn quản lý user_id
                self.file_path = self.get_file_path(self.file_id, self.user_id)
                
            # Xác định số dòng cần lấy mẫu
            sample_rows = None
            if sample:
                sample_rows = max_rows or self.max_rows_preview
            
            # Tải dữ liệu
            df = await self.validation_service.validate_and_load_file(
                self.file_path,
                sample_rows=sample_rows
            )
            
            # Không thể xử lý nếu không có dữ liệu
            if df is None or len(df) == 0:
                return pd.DataFrame(), {"error": "No data loaded"}
            
            # Xác thực chất lượng dữ liệu
            quality_report = await self.validation_service.validate_data_quality(df)
            
            # Tối ưu memory nếu DataFrame lớn
            df_size_mb = estimate_dataframe_size(df)
            if df_size_mb > 50:  # > 50MB
                df = optimize_dataframe_memory(df)
            
            return df, quality_report
        except Exception as e:
            logger.error(f"Error loading and validating data: {str(e)}", exc_info=True)
            return pd.DataFrame(), {"error": str(e)}

    async def generate_insights(
        self, 
        df: pd.DataFrame, 
        insight_types: Optional[List[str]] = None,
        query: Optional[str] = None
    ) -> List[InsightData]:
        """
        Tạo insights không đồng bộ, hỗ trợ phân tích dựa trên query
        
        Args:
            df: DataFrame cần phân tích
            insight_types: Loại insights cần tạo (nếu None, tự động chọn)
            query: Câu hỏi người dùng (optional) - dùng để phân tích hướng dẫn
            
        Returns:
            List[InsightData]: Danh sách insights
        """
        try:
            # Phân tích intent từ query nếu có
            intent = None
            target_columns = None
            if query and self.intent_service:
                try:
                    user_intent = await self.intent_service.detect_intent(query, df=df)
                    intent = user_intent.intent
                    target_columns = user_intent.columns
                    
                    # Tự động xác định insight_types dựa trên intent
                    if intent and not insight_types:
                        if intent == IntentType.INSIGHT:
                            insight_types = ["DISTRIBUTION", "CORRELATION", "PATTERN"]
                        elif intent == IntentType.ANALYSIS:
                            insight_types = ["CORRELATION", "OUTLIER", "TREND"]
                        elif intent == IntentType.VISUALIZATION:
                            insight_types = ["DISTRIBUTION", "TREND"]
                except Exception as intent_error:
                    logger.warning(f"Error detecting intent: {str(intent_error)}")
            
            # Check if we have cached insights với query context
            cache_params = {
                "insight_types": insight_types,
                "query": query,
                "target_columns": target_columns,
                "file_id": self.file_id
            }
            cache_key = self._generate_cache_key("insights", cache_params)
            cached_result = self.inference_cache.get(cache_key)
            if cached_result:
                logger.info("Using cached insights")
                return cached_result
            
            # Ước tính dataframe size để quyết định xử lý
            df_size_mb = estimate_dataframe_size(df)
            logger.info(f"DataFrame size estimate: {df_size_mb:.2f} MB")
            
            # Process với target columns nếu có
            if target_columns:
                # Đảm bảo tất cả target columns tồn tại trong DataFrame
                valid_columns = [col for col in target_columns if col in df.columns]
                if valid_columns:
                    df_subset = df[valid_columns]
                else:
                    df_subset = df
            else:
                df_subset = df
            
            # Với DataFrame lớn, sử dụng executor
            if df_size_mb > 100:  # > 100MB
                logger.info("Using ThreadPoolExecutor for large DataFrame")
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future = executor.submit(
                        self.data_analyzer.run_analysis, df_subset, "insights", self.file_id, insight_types
                    )
                    # Đợi kết quả
                    analysis_results = await asyncio.get_event_loop().run_in_executor(
                        None, future.result
                    )
            else:
                # Với DataFrame nhỏ hơn, chạy trực tiếp
                analysis_results = self.data_analyzer.run_analysis(df_subset, "insights", self.file_id, insight_types)
            
            # Kiểm tra lỗi từ analyzer
            if "error" in analysis_results:
                logger.error(f"Error from analyzer: {analysis_results['error']}")
                return []
                
            insights = analysis_results.get("insights", [])
            # insights = [ insight for insight in insights if isinstance(insight, InsightData)]
            
            # Thêm advanced insights từ time_series nếu phù hợp
            target_column = target_columns[0] if target_columns and len(target_columns) > 0 else None
            advanced_insights = self.generate_advanced_insights(df, target_column)
            
            # Kết hợp và sắp xếp insights theo importance
            all_insights = insights + advanced_insights
            all_insights = sorted(all_insights, key=lambda x: x.get("importance", 0), reverse=True)
            
            # Giới hạn số lượng insights (nếu quá nhiều)
            if len(all_insights) > 10:
                all_insights = all_insights[:10]
            
            # Cache kết quả
            self.inference_cache.set(cache_key, all_insights)
            
            return all_insights
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}", exc_info=True)
            return []
        
    async def generate_visualizations(
        self, 
        df: pd.DataFrame, 
        chart_types: Optional[List[str]] = None,
        query: Optional[str] = None
    ) -> List[VisualizationData]:
        """
        Tạo biểu đồ không đồng bộ, hỗ trợ phân tích dựa trên query
        
        Args:
            df: DataFrame cần phân tích
            chart_types: Loại biểu đồ cần tạo (nếu None, tự động chọn)
            query: Câu hỏi người dùng (optional) - dùng để định hướng visualization
            
        Returns:
            List[VisualizationData]: Danh sách biểu đồ
        """
        try:
            # Phân tích intent từ query nếu có
            viz_type = None
            target_columns = None
            if query and self.intent_service:
                try:
                    user_intent = await self.intent_service.detect_intent(query, df=df)
                    if user_intent.intent == IntentType.VISUALIZATION:
                        viz_type = user_intent.visualization_type
                        target_columns = user_intent.columns
                except Exception as intent_error:
                    logger.warning(f"Error detecting intent: {str(intent_error)}")
            
            # Check if we have cached visualizations với query context
            cache_params = {
                "chart_types": chart_types,
                "viz_type": viz_type,
                "target_columns": target_columns,
                "query": query,
                "file_id": self.file_id
            }
            cache_key = self._generate_cache_key("visualizations", cache_params)
            cached_result = self.inference_cache.get(cache_key)
            if cached_result:
                logger.info("Using cached visualizations")
                return cached_result
            
            # Ước tính dataframe size để quyết định xử lý
            df_size_mb = estimate_dataframe_size(df)
            
            # Nếu phát hiện intent visualization cụ thể, tạo trực tiếp
            if viz_type and target_columns:
                # Đảm bảo target_columns tồn tại trong DataFrame
                valid_columns = [col for col in target_columns if col in df.columns]
                if valid_columns:
                    # Tạo visualization cụ thể với chart recommender
                    recommended_chart = self.chart_recommender.create_recommended_chart(
                        df[valid_columns], valid_columns, viz_type
                    )
                    if recommended_chart:
                        # Cache kết quả
                        visualizations = [recommended_chart]
                        self.inference_cache.set(cache_key, visualizations)
                        return visualizations
            
            # Process với target columns nếu có và không phải là visualization cụ thể
            if target_columns:
                valid_columns = [col for col in target_columns if col in df.columns]
                if valid_columns:
                    df_subset = df[valid_columns]
                else:
                    df_subset = df
            else:
                df_subset = df
            
            # Với DataFrame lớn, sử dụng executor
            if df_size_mb > 100:  # > 100MB
                logger.info("Using ThreadPoolExecutor for large DataFrame")
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future = executor.submit(
                        self.data_analyzer.run_analysis, df_subset, "visualizations", self.file_id, chart_types
                    )
                    # Đợi kết quả
                    analysis_results = await asyncio.get_event_loop().run_in_executor(
                        None, future.result
                    )
            else:
                # Với DataFrame nhỏ hơn, chạy trực tiếp
                analysis_results = self.data_analyzer.run_analysis(df_subset, "visualizations", self.file_id, chart_types)
            
            # Kiểm tra lỗi từ analyzer
            if "error" in analysis_results:
                logger.error(f"Error from analyzer: {analysis_results['error']}")
                return []
                
            visualizations = analysis_results.get("visualizations", [])
            
            # Cache kết quả
            self.inference_cache.set(cache_key, visualizations)
            
            return visualizations
        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}", exc_info=True)
            return []

    async def make_prediction(
        self, 
        df: pd.DataFrame, 
        prediction_config: PredictionConfig,
        preprocess: bool = True
    ) -> PredictionResult:
        """
        Tạo dự đoán không đồng bộ với tiền xử lý tự động
        
        Args:
            df: DataFrame chứa dữ liệu
            prediction_config: Cấu hình dự đoán
            preprocess: Có tiền xử lý dữ liệu không
            
        Returns:
            PredictionResult: Kết quả dự đoán
        """
        try:
            if not self.model_service:
                raise ValueError("ModelService is required for predictions but not provided")
                
            # Dự đoán không lưu cache vì thường unique
            if preprocess:
                # Sử dụng data_processor từ ML module thay vì hàm clean tự định nghĩa
                processed_df = self.data_processor.process(df)
            else:
                processed_df = df
                
            prediction_type = prediction_config.modelType.lower()
            
            # Kiểm tra nếu prediction là time series và sử dụng time_series_analyzer
            if prediction_type == "time_series":
                return await self._make_time_series_prediction(processed_df, prediction_config)
            
            # Dự đoán với model service
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future = executor.submit(
                    self.model_service.predict,
                    processed_df, 
                    prediction_config.targetColumn, 
                    prediction_config.featureColumns,
                    prediction_config.modelType
                )
                
                # Đợi kết quả
                model_result = await asyncio.get_event_loop().run_in_executor(
                    None, future.result
                )
            
            return await self._convert_model_result_to_prediction(model_result, prediction_config)
        except Exception as e:
            logger.error(f"Error making prediction: {str(e)}", exc_info=True)
            raise
    
    async def _make_time_series_prediction(
        self, 
        df: pd.DataFrame, 
        prediction_config: PredictionConfig
    ) -> PredictionResult:
        """
        Tạo dự đoán time series với time_series_analyzer
        
        Args:
            df: DataFrame đã xử lý
            prediction_config: Cấu hình dự đoán
            
        Returns:
            PredictionResult: Kết quả dự đoán
        """
        try:
            # Tìm cột datetime để sử dụng cho time series
            datetime_cols = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
            
            if not datetime_cols:
                raise ValueError("No datetime column found for time series prediction")
                
            date_col = datetime_cols[0]
            target_col = prediction_config.targetColumn
            
            if not pd.api.types.is_numeric_dtype(df[target_col]):
                raise ValueError(f"Target column {target_col} must be numeric for time series prediction")
            
            # Dự đoán với time_series_analyzer từ ML module
            forecast_periods = prediction_config.horizon or 10
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    self.time_series_analyzer.forecast_time_series,
                    df,
                    date_col,
                    target_col,
                    forecast_periods,
                    True  # return_confidence
                )
                
                # Đợi kết quả
                forecast_result = await asyncio.get_event_loop().run_in_executor(
                    None, future.result
                )
            
            # Convert forecast result to PredictionResult
            predictions = []
            for i, point in enumerate(forecast_result.get("forecast_data", [])):
                predictions.append({
                    "time": point.get("date"),
                    "actual": None,  # No actual values for forecasts
                    "predicted": point.get("forecast"),
                    "lower_bound": point.get("lower_bound"),
                    "upper_bound": point.get("upper_bound")
                })
            
            # Create visualization
            visualization = await self._create_time_series_forecast_visualization(
                predictions, date_col, target_col
            )
            
            # Get model info and metrics
            model_info = forecast_result.get("analysis", {})
            metrics = forecast_result.get("metrics", {})
            
            # Extract insights
            insights = forecast_result.get("insights", [])
            
            return PredictionResult(
                predictions=predictions,
                metrics=metrics,
                modelInfo=model_info,
                importance={},  # No feature importance for time series
                visualization=visualization,
                insights=insights
            )
        except Exception as e:
            logger.error(f"Error making time series prediction: {str(e)}", exc_info=True)
            raise
    
    async def run_analysis(
        self,
        df: pd.DataFrame,
        analysis_type: str = "full",
        query: Optional[str] = None,
        use_ml: bool = False
    ) -> Dict:
        """
        Comprehensive analysis with async processing and query guidance
        
        Args:
            df: DataFrame to analyze
            query: User query (optional) to guide analysis
            use_ml: Whether to use ML for insight generation (slower but more contextual)
            
        Returns:
            Dict: Comprehensive analysis results
        """
        try:
            # Check cache
            cache_params = {"file_id": self.file_id, "query": query, "use_ml": use_ml}
            cache_key = self._generate_cache_key("full-analysis", cache_params)
            cached_result = self.inference_cache.get(cache_key)
            if cached_result:
                logger.info("Using cached full analysis results")
                return cached_result
            
            target_columns = None
            
            if query and self.intent_service:
                try:
                    user_intent = await self.intent_service.detect_intent(query, df=df)
                    
                    # Adjust analysis type based on intent
                    if user_intent.intent == IntentType.VISUALIZATION:
                        analysis_type = "visualizations"
                    elif user_intent.intent == IntentType.INSIGHT:
                        analysis_type = "insights"
                    elif user_intent.intent == IntentType.ANALYSIS:
                        analysis_type = "advanced"
                    
                    target_columns = user_intent.columns
                except Exception as intent_error:
                    logger.warning(f"Error detecting intent: {str(intent_error)}")
            
            # Process with target columns if available
            if target_columns:
                valid_columns = [col for col in target_columns if col in df.columns]
                if valid_columns:
                    df_subset = df[valid_columns]
                else:
                    df_subset = df
            else:
                df_subset = df
            
            # Preprocess DataFrame
            processed_df = self.preprocess_dataframe(df_subset)
            
            # Use async with threadpool
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit analysis task with use_ml parameter
                future = executor.submit(
                    self.data_analyzer.run_analysis, 
                    processed_df, 
                    analysis_type,
                    self.file_id,
                    filter_types=None,
                    use_ml=use_ml
                )
                
                # Wait for result
                result = await asyncio.get_event_loop().run_in_executor(
                    None, future.result
                )
            
            # Convert NumPy types to Python native types
            result = self._convert_numpy_types(result)

            # Save to cache
            self.inference_cache.set(cache_key, result)
            
            return result
        except Exception as e:
            logger.error(f"Error running full analysis: {str(e)}", exc_info=True)
            raise

    async def run_analysis_batched(
        self, 
        df: pd.DataFrame, 
        analysis_type: str = "full",
        target_columns: Optional[List[str]] = None,
        batch_size: int = 10000
    ) -> Dict:
        """
        Chạy phân tích toàn diện theo batch cho DataFrame lớn
        
        Args:
            df: DataFrame cần phân tích
            analysis_type: Loại phân tích cần thực hiện
            target_columns: Các cột target nếu có
            batch_size: Kích thước mỗi batch
            
        Returns:
            Dict: Kết quả phân tích
        """
        try:
            # Kiểm tra cache
            cache_params = {
                "file_id": self.file_id, 
                "analysis_type": analysis_type, 
                "target_columns": target_columns
            }
            cache_key = self._generate_cache_key("batched-analysis", cache_params)
            cached_result = self.inference_cache.get(cache_key)
            if cached_result:
                logger.info("Using cached batched analysis results")
                return cached_result
            
            # Khởi tạo kết quả tổng hợp
            result = {
                "dataset_info": None,
                "data_quality": {},
                "statistical_analysis": self._init_empty_statistical_analysis(),
                "insights": [],
                "visualizations": [],
                "recommendations": []
            }
            
            # Lọc DataFrame với target columns nếu có
            if target_columns:
                valid_columns = [col for col in target_columns if col in df.columns]
                if valid_columns:
                    df_filtered = df[valid_columns].copy()
                else:
                    df_filtered = df.copy()
            else:
                df_filtered = df.copy()
            
            # Sử dụng memory_utils.chunk_dataframe để chia batch thông minh
            chunks = chunk_dataframe(df_filtered, max_chunk_size_mb=100, min_rows_per_chunk=1000)
            num_batches = len(chunks)
            
            if num_batches == 0:
                raise ValueError("No valid chunks created from DataFrame")
                
            logger.info(f"Processing DataFrame in {num_batches} chunks")
            
            # Biến tạm để tính toán thống kê toàn cục
            total_rows = 0
            column_types = None
            numeric_stats = {}
            categorical_counts = {}
            
            # Xử lý từng batch
            for batch_idx, batch_df in enumerate(chunks):
                logger.info(f"Processing batch {batch_idx+1}/{num_batches}, rows: {len(batch_df)}")
                
                # Làm sạch và tiền xử lý dữ liệu
                try:
                    batch_processed = self.preprocess_dataframe(batch_df)
                except Exception as e:
                    logger.error(f"Error preprocessing batch {batch_idx+1}: {str(e)}")
                    continue
                
                # Cập nhật dataset_info lần đầu
                if result["dataset_info"] is None:
                    try:
                        result["dataset_info"] = self.data_analyzer._analyze_dataset_info(df_filtered)
                        result["dataset_info"]["total_batches"] = num_batches
                    except Exception as e:
                        logger.error(f"Error analyzing dataset info: {str(e)}")
                        result["dataset_info"] = {
                            "rows": len(df_filtered),
                            "columns": len(df_filtered.columns),
                            "total_batches": num_batches,
                            "error": str(e)
                        }
                
                # Cập nhật tổng số dòng
                total_rows += len(batch_df)
                
                # Cập nhật column types
                if column_types is None:
                    try:
                        column_types = self.detect_column_types(batch_processed)
                    except Exception as e:
                        logger.error(f"Error detecting column types: {str(e)}")
                
                # Xử lý không đồng bộ
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit batch analysis task
                    future = executor.submit(
                        self._process_batch,
                        batch_processed,
                        batch_idx,
                        numeric_stats,
                        categorical_counts,
                        analysis_type
                    )
                    
                    # Đợi kết quả
                    batch_result = await asyncio.get_event_loop().run_in_executor(
                        None, future.result
                    )
                
                # Cập nhật numeric_stats và categorical_counts
                numeric_stats = batch_result["numeric_stats"]
                categorical_counts = batch_result["categorical_counts"]
                
                # Cập nhật insights và visualizations
                for insight in batch_result["insights"]:
                    if isinstance(insight, dict) and "title" in insight:
                        # Check if we already have this insight
                        if not any(i.get("title") == insight["title"] for i in result["insights"] 
                               if isinstance(i, dict) and "title" in i):
                            result["insights"].append(insight)
                    else:
                        # For InsightData objects
                        if not any(i.title == insight.title for i in result["insights"] 
                               if hasattr(i, "title")):
                            result["insights"].append(insight)
                
                for viz in batch_result["visualizations"]:
                    if isinstance(viz, dict) and "title" in viz:
                        # Check if we already have this visualization
                        if not any(v.get("title") == viz["title"] for v in result["visualizations"]
                               if isinstance(v, dict) and "title" in v):
                            result["visualizations"].append(viz)
                    else:
                        # For VisualizationData objects
                        if not any(v.title == viz.title for v in result["visualizations"]
                               if hasattr(v, "title")):
                            result["visualizations"].append(viz)
                
                # Cập nhật recommendations
                for rec in batch_result["recommendations"]:
                    if rec not in result["recommendations"]:
                        result["recommendations"].append(rec)
            
            # Cập nhật thông tin cuối cùng
            if result["dataset_info"]:
                result["dataset_info"]["rows"] = total_rows
            
            # Tính toán thống kê toàn cục từ thống kê từng batch
            result["statistical_analysis"] = self._compute_global_statistics(
                numeric_stats, categorical_counts, total_rows
            )
            
            # Sắp xếp insights theo importance
            result["insights"] = sorted(
                result["insights"], 
                key=lambda x: (x.importance if hasattr(x, "importance") else 
                              (x.get("importance", 0) if isinstance(x, dict) else 0)), 
                reverse=True
            )[:10]  # Chỉ giữ top 10 insights
            
            # Giới hạn số lượng visualizations
            result["visualizations"] = result["visualizations"][:5]
            
            # Chuyển đổi các kiểu dữ liệu NumPy sang Python native types
            result = self._convert_numpy_types(result)
            
            # Lưu kết quả vào cache
            self.inference_cache.set(cache_key, result)
            
            return result
        except Exception as e:
            logger.error(f"Error in batched analysis: {str(e)}", exc_info=True)
            return {"error": str(e)}
        
    def _process_batch(
        self, 
        batch_df: pd.DataFrame, 
        batch_idx: int,
        numeric_stats: Dict,
        categorical_counts: Dict,
        analysis_type: str = "full"
    ) -> Dict:
        """
        Xử lý một batch trong batched analysis
        
        Args:
            batch_df: DataFrame batch
            batch_idx: Index của batch
            total_batches: Tổng số batch
            numeric_stats: Dict lưu trữ thống kê
            categorical_counts: Dict lưu trữ tần suất
            analysis_type: Loại phân tích
            
        Returns:
            Dict: Kết quả xử lý batch
        """
        try:
            batch_result = {
                "insights": [],
                "visualizations": [],
                "recommendations": [],
                "numeric_stats": numeric_stats.copy() if numeric_stats else {},
                "categorical_counts": categorical_counts.copy() if categorical_counts else {}
            }
            
            # Nếu batch đủ lớn và có ý nghĩa, chạy phân tích
            if len(batch_df) >= 100:
                # Chạy phân tích trên batch
                try:
                    analysis = self.data_analyzer.run_analysis(batch_df, file_id=self.file_id, analysis_type=analysis_type)
                    column_types = self.detect_column_types(batch_df)

                    # Cập nhật insights và visualizations
                    batch_result["insights"].extend(analysis.get("insights", []))
                    batch_result["visualizations"].extend(analysis.get("visualizations", []))
                    batch_result["recommendations"].extend(analysis.get("recommendations", []))
                    
                    # Thêm advanced insights cho batch đầu tiên
                    if batch_idx == 0:
                        try:
                            advanced_insights = self.generate_advanced_insights(batch_df)
                            batch_result["insights"].extend(advanced_insights)
                        except Exception as e:
                            logger.error(f"Error generating advanced insights: {str(e)}")
                except Exception as e:
                    logger.error(f"Error analyzing batch {batch_idx+1}: {str(e)}")
            
            # Cập nhật thống kê cho các cột numeric
            for col in column_types["numeric"]:
                if col not in batch_result["numeric_stats"]:
                    batch_result["numeric_stats"][col] = {
                        "sum": 0, "sum_squares": 0, "min": float('inf'), 
                        "max": float('-inf'), "count": 0
                    }
                
                non_na = batch_df[col].dropna()
                if len(non_na) > 0:
                    batch_result["numeric_stats"][col]["sum"] += non_na.sum()
                    batch_result["numeric_stats"][col]["sum_squares"] += (non_na ** 2).sum()
                    batch_result["numeric_stats"][col]["min"] = min(
                        batch_result["numeric_stats"][col]["min"], 
                        non_na.min()
                    )
                    batch_result["numeric_stats"][col]["max"] = max(
                        batch_result["numeric_stats"][col]["max"], 
                        non_na.max()
                    )
                    batch_result["numeric_stats"][col]["count"] += len(non_na)
            
            # Cập nhật thống kê cho các cột categorical
            for col in column_types["categorical"]:
                if col not in batch_result["categorical_counts"]:
                    batch_result["categorical_counts"][col] = {}
                
                # Cập nhật value counts
                value_counts = batch_df[col].value_counts().to_dict()
                for val, count in value_counts.items():
                    if val in batch_result["categorical_counts"][col]:
                        batch_result["categorical_counts"][col][val] += count
                    else:
                        batch_result["categorical_counts"][col][val] = count
            
            return batch_result
        except Exception as e:
            logger.error(f"Error processing batch {batch_idx+1}: {str(e)}", exc_info=True)
            return {
                "insights": [],
                "visualizations": [],
                "recommendations": [],
                "numeric_stats": numeric_stats,
                "categorical_counts": categorical_counts
            }
        
    def _init_empty_statistical_analysis(self) -> Dict:
        """Khởi tạo cấu trúc trống cho statistical_analysis"""
        return {
            "numeric_summary": {},
            "categorical_summary": {},
            "datetime_summary": {},
            "correlation_matrix": {},
            "group_statistics": []
        }
    
    def _compute_global_statistics(
        self, 
        numeric_stats: Dict[str, Dict], 
        categorical_counts: Dict[str, Dict],
        total_rows: int
    ) -> Dict:
        """Tính toán thống kê toàn cục từ thống kê từng batch"""
        result = self._init_empty_statistical_analysis()
        
        # Tính toán thống kê cho các cột numeric
        for col, stats in numeric_stats.items():
            if stats["count"] > 0:
                mean = stats["sum"] / stats["count"]
                variance = (stats["sum_squares"] / stats["count"]) - (mean ** 2)
                std_dev = math.sqrt(variance) if variance > 0 else 0
                
                result["numeric_summary"][col] = {
                    "count": int(stats["count"]),  # Chuyển đổi sang int
                    "mean": float(mean),  # Chuyển đổi sang float
                    "std": float(std_dev),
                    "min": float(stats["min"]) if stats["min"] != float('inf') else 0,
                    "max": float(stats["max"]) if stats["max"] != float('-inf') else 0
                }
        
        # Tính toán thống kê cho các cột categorical
        for col, counts in categorical_counts.items():
            # Sắp xếp và lấy top giá trị
            sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
            top_values = {str(k): int(v) for k, v in sorted_counts[:10]}  # Chuyển đổi sang int
            
            unique_count = len(counts)
            
            result["categorical_summary"][col] = {
                "unique_values": int(unique_count),  # Chuyển đổi sang int
                "top_values": top_values,
                "mode": str(sorted_counts[0][0]) if sorted_counts else None
            }
        
        # Chuyển đổi toàn bộ kết quả
        return self._convert_numpy_types(result)
    
    async def _convert_model_result_to_prediction(
        self, 
        model_result: Dict, 
        config: PredictionConfig
    ) -> PredictionResult:
        """
        Convert model result to prediction result
        
        Args:
            model_result: Kết quả từ model
            config: Cấu hình dự đoán
            
        Returns:
            PredictionResult: Kết quả dự đoán
        """
        predictions = model_result.get("predictions", [])
        metrics = model_result.get("metrics", {})
        model_info = model_result.get("model_info", {})
        importance = model_result.get("feature_importance", {})

        # Create visualization in background
        visualization = await self._create_prediction_visualization(predictions, config)

        return PredictionResult(
            predictions=predictions,
            metrics=metrics,
            modelInfo=model_info,
            importance=importance,
            visualization=visualization
        )
    
    async def _create_prediction_visualization(
        self, 
        predictions: List[Dict], 
        config: PredictionConfig
    ) -> Optional[VisualizationData]:
        """
        Create visualization for prediction
        
        Args:
            predictions: Kết quả dự đoán
            config: Cấu hình dự đoán
            
        Returns:
            Optional[VisualizationData]: Biểu đồ kết quả dự đoán
        """
        try:
            if not predictions:
                return None
                
            if config.modelType.lower() == "regression":
                data = [
                    {"actual": p.get("actual", 0), "predicted": p.get("predicted", 0), "index": i}
                    for i, p in enumerate(predictions)
                ]
                
                chart = VisualizationData(
                    id=str(v4()),
                    fileId=self.file_id,
                    type=ChartType.SCATTER,
                    title=f"Actual vs Predicted {config.targetColumn}",
                    description="Comparison of actual and predicted values",
                    data=data,
                    config={
                        "xAxis": {"key": "actual", "name": "Actual Values"},
                        "yAxis": {"key": "predicted", "name": "Predicted Values"},
                        "width": 600,
                        "height": 400,
                        "showTrendline": True
                    }
                )
                return chart
                
            elif config.modelType.lower() == "classification":
                # Create confusion matrix visualization
                if len(predictions) > 0 and "class_probs" in predictions[0]:
                    # Extract classes from first prediction
                    classes = list(predictions[0]["class_probs"].keys())
                    
                    # Create confusion matrix data
                    confusion_data = []
                    for cls_actual in classes:
                        for cls_pred in classes:
                            count = sum(1 for p in predictions 
                                    if p.get("actual") == cls_actual and p.get("predicted") == cls_pred)
                            confusion_data.append({
                                "actual": cls_actual,
                                "predicted": cls_pred,
                                "count": count
                            })
                    
                    return VisualizationData(
                        id=str(v4()),
                        fileId=self.file_id,
                        type=ChartType.HEATMAP,
                        title="Confusion Matrix",
                        description="Confusion matrix showing actual vs predicted classes",
                        data=confusion_data,
                        config={
                            "xAxis": {"key": "predicted", "name": "Predicted Class"},
                            "yAxis": {"key": "actual", "name": "Actual Class"},
                            "colorKey": "count",
                            "width": 500,
                            "height": 500
                        }
                    )
                return None
            
            return None
        except Exception as e:
            logger.warning(f"Error creating prediction visualization: {str(e)}", exc_info=True)
            return None
    
    async def _create_time_series_forecast_visualization(
        self, 
        predictions: List[Dict], 
        time_column: str,
        value_column: str
    ) -> Optional[VisualizationData]:
        """
        Create time series forecast visualization
        
        Args:
            predictions: Kết quả dự đoán time series
            time_column: Tên cột thời gian
            value_column: Tên cột giá trị
            
        Returns:
            Optional[VisualizationData]: Biểu đồ dự đoán time series
        """
        try:
            if not predictions:
                return None
                
            # Tạo biểu đồ time series
            return VisualizationData(
                id=str(v4()),
                fileId=self.file_id,
                type=ChartType.LINE,
                title=f"Time Series Forecast for {value_column}",
                description="Time series forecast with confidence intervals",
                data=predictions,
                config={
                    "xAxis": {"key": "time", "name": time_column},
                    "yAxis": {"key": "predicted", "name": f"Forecasted {value_column}"},
                    "width": 800,
                    "height": 400,
                    "showConfidenceInterval": True,
                    "lowerBoundKey": "lower_bound",
                    "upperBoundKey": "upper_bound"
                }
            )
        except Exception as e:
            logger.warning(f"Error creating time series visualization: {str(e)}", exc_info=True)
            return None
        
    async def answer_query(
        self, 
        df: pd.DataFrame, 
        query: str, 
        message_history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Trả lời câu hỏi về dữ liệu sử dụng IntentService và phân tích dữ liệu
        
        Args:
            df: DataFrame chứa dữ liệu
            query: Câu hỏi từ người dùng
            message_history: Lịch sử tin nhắn
            
        Returns:
            Dict: Kết quả phân tích và trả lời
        """
        try:
            if not self.intent_service:
                raise ValueError("IntentService is required for answering queries")
                
            # Phát hiện intent
            user_intent = await self.intent_service.detect_intent(query, message_history, df)
            
            # Xử lý dựa trên intent
            if user_intent.intent == IntentType.VISUALIZATION:
                # Tạo visualization
                visualizations = await self.generate_visualizations(df, None, query)
                return {
                    "intent": user_intent.intent,
                    "confidence": user_intent.confidence,
                    "visualizations": visualizations,
                    "answer": f"Here's a visualization for your query about {', '.join(user_intent.columns) if user_intent.columns else 'the data'}"
                }
            
            elif user_intent.intent == IntentType.INSIGHT:
                # Tạo insights
                insights = await self.generate_insights(df, None, query)
                return {
                    "intent": user_intent.intent,
                    "confidence": user_intent.confidence,
                    "insights": insights,
                    "answer": f"Here are some insights about {', '.join(user_intent.columns) if user_intent.columns else 'the data'}"
                }
                
            elif user_intent.intent == IntentType.ANALYSIS:
                # Chạy phân tích
                analysis = await self.run_analysis(df, analysis_type="full", query=query)
                return {
                    "intent": user_intent.intent,
                    "confidence": user_intent.confidence,
                    "analysis": analysis,
                    "answer": f"I've analyzed {', '.join(user_intent.columns) if user_intent.columns else 'the data'} for you"
                }
                
            else:
                # Mặc định trả về thông tin cơ bản
                return {
                    "intent": user_intent.intent,
                    "confidence": user_intent.confidence,
                    "answer": "I'm not sure how to process that query. Try asking for specific insights, visualizations, or analysis."
                }
        except Exception as e:
            logger.error(f"Error answering query: {str(e)}", exc_info=True)
            return {"error": str(e)}
        
    async def health_check(self) -> Dict[str, Any]:
        """Kiểm tra sức khỏe của service với thông tin chi tiết hơn"""
        try:
            health_info = {
                "status": "healthy",
                "file_id": self.file_id,
                "file_path": self.file_path,
                "cache_stats": self.inference_cache.get_stats() if hasattr(self.inference_cache, "get_stats") else {},
                "components": {}
            }
            
            # Kiểm tra các ML components
            try:
                health_info["components"]["data_processor"] = "available" if self._data_processor else "not_initialized"
            except:
                health_info["components"]["data_processor"] = "error"
                
            try:
                health_info["components"]["data_analyzer"] = "available" if self._data_analyzer else "not_initialized"
            except:
                health_info["components"]["data_analyzer"] = "error"
                
            try:
                health_info["components"]["chart_generator"] = "available" if self._chart_generator else "not_initialized"
            except:
                health_info["components"]["chart_generator"] = "error"
                
            try:
                health_info["components"]["insight_generator"] = "available" if self._insight_generator else "not_initialized"
            except:
                health_info["components"]["insight_generator"] = "error"
            
            # Kiểm tra các services
            health_info["services"] = {
                "model_service": "available" if self.model_service else "not_provided",
                "intent_service": "available" if self.intent_service else "not_provided",
                "validation_service": "available" if self.validation_service else "not_provided"
            }
            
            # Kiểm tra file tồn tại
            health_info["file_exists"] = os.path.exists(self.file_path) if self.file_path else False
            
            return health_info
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}", exc_info=True)
            return {
                "status": "unhealthy",
                "error": str(e)
            }