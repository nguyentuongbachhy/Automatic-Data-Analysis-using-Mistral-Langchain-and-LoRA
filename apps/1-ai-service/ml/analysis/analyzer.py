import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple

import pandas as pd
import numpy as np
from pandas.api.types import is_numeric_dtype
from scipy import stats

# Import modules
from ml.data.data_processor import DataProcessor
from ml.data.data_validator import DataValidator
from ml.visualization.charts import ChartGenerator
from ml.visualization.insights import InsightGenerator
from ml.visualization.recommender import ChartRecommender
from ml.analysis.time_series import TimeSeriesAnalyzer
from ml.utils.datetime_utils import convert_to_datetime, is_datetime, analyze_datetime_distribution
from ml.utils.memory_utils import optimize_dataframe_memory

logger = logging.getLogger(__name__)


class DataAnalyzer:
    """Phân tích dữ liệu tự động và toàn diện với tính năng ML/DL nâng cao"""

    def __init__(self, config_path: Optional[Union[str, Dict]] = None):
        """Khởi tạo analyzer với config tùy chọn"""
        # Tải config
        self.config = self._load_config(config_path)
        
        # Khởi tạo các thành phần
        self.data_processor = DataProcessor(self.config)
        self.data_validator = DataValidator(self.config)
        self.chart_generator = ChartGenerator(config_path=self.config)
        self.insight_generator = InsightGenerator()
        self.chart_recommender = ChartRecommender(self.config)
        self.time_series_analyzer = TimeSeriesAnalyzer()
        self.column_types = {}
        
        # Thêm thông tin version và memory tracking
        self.version = "2.0.0"
        self.memory_tracker = {"initial": 0, "optimized": 0, "reduction": 0}

        logger.info(f"Enhanced DataAnalyzer v{self.version} initialized")
    
    def _load_config(self, config_path: Optional[Union[str, Dict]]) -> Dict:
        """Tải config từ file hoặc dict"""
        try:
            if isinstance(config_path, dict):
                return config_path
            
            if not config_path:
                config_path = os.getenv("MODEL_CONFIG_PATH", "configs/model_config.json")
                
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.warning(f"Config file {config_path} not found, using default configuration")
            
            # Cấu hình mặc định cải tiến với thêm nhiều options
            return {
                "data_processing": {
                    "max_rows_preview": 100,
                    "max_rows_analysis": 100000,
                    "sample_method": "random", 
                    "outlier_threshold": 3,
                    "categorical_threshold": 20,
                    "missing_values_threshold": 0.8,
                    "correlation_threshold": 0.7,
                    "enable_advanced_imputation": True,
                    "enable_feature_engineering": True,
                    "memory_optimization_level": "high"  # 'none', 'low', 'medium', 'high'
                },
                "visualization": {
                    "default_chart_height": 400,
                    "default_chart_width": 600,
                    "color_palette": "tableau10",
                    "max_categories_in_chart": 12,
                    "max_charts_per_insight": 5,
                    "max_points_in_scatter": 5000,
                    "enable_interactive_charts": True
                },
                "ml": {
                    "enable_clustering": True,
                    "enable_advanced_forecasting": True,
                    "feature_importance_method": "shap",  # 'shap', 'permutation', 'pca'
                    "max_clusters": 10
                }
            }
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return {
                "data_processing": {
                    "max_rows_preview": 100,
                    "max_rows_analysis": 100000,
                    "outlier_threshold": 3
                },
                "visualization": {
                    "default_chart_height": 400,
                    "default_chart_width": 600
                }
            }
    
    def run_analysis(self, df: pd.DataFrame, analysis_type: str = "full",
                file_id: Optional[str] = None,
                filter_types: Optional[List[str]] = None, use_ml: bool = False,
                optimize_memory: bool = True, use_parallel: bool = True) -> Dict:
        """
        Phân tích dữ liệu tự động và toàn diện với nhiều cải tiến
        
        Args:
            df: DataFrame cần phân tích
            analysis_type: Loại phân tích ("full", "quality", "statistics", "insights", 
                        "visualizations", "advanced", "time_series")
            filter_types: Lọc theo loại insight/visualization
            use_ml: Sử dụng ML-based insights
            optimize_memory: Tối ưu bộ nhớ sử dụng
            use_parallel: Cho phép xử lý song song
            
        Returns:
            Dict: Kết quả phân tích
        """
        try:
            # Tính thời gian thực hiện
            start_time = time.time()
            
            # Khởi tạo kết quả với thêm metadata và version
            analysis_results = {
                "metadata": {
                    "analyzer_version": self.version,
                    "analysis_type": analysis_type,
                    "file_id": file_id,
                    "timestamp": datetime.now().isoformat(),
                    "rows_analyzed": len(df),
                    "columns_analyzed": len(df.columns)
                },
                "dataset_info": {},
                "data_quality": {},
                "statistical_analysis": {},
                "advanced_analysis": {},
                "insights": [],
                "visualizations": [],
                "recommendations": [],
                "performance_metrics": {},
                "createdAt": datetime.now(),
                "updatedAt": datetime.now()
            }

            # Phát hiện column types
            self.column_types = self._detect_column_types(df)
            
            # Tối ưu bộ nhớ với cải tiến sử dụng hàm riêng
            if optimize_memory:
                df, memory_metrics = self._optimize_memory_usage(df)
                analysis_results["performance_metrics"]["memory_optimization"] = memory_metrics
                logger.info(f"Optimized memory usage: {memory_metrics['before_mb']:.2f}MB -> "
                         f"{memory_metrics['after_mb']:.2f}MB "
                         f"({memory_metrics['reduction_percent']}% reduction)")
            
            # Sampling nếu cần với nhiều phương pháp hơn
            df = self._sample_dataframe(df)
            
            # Phân tích thông tin dataset - luôn thực hiện
            logger.info("Starting dataset info analysis")
            dataset_info_start = time.time()
            analysis_results["dataset_info"] = self._analyze_dataset_info(df)
            analysis_results["performance_metrics"]["dataset_info_time"] = round(time.time() - dataset_info_start, 3)
            logger.info("Dataset info analysis completed")

            # Chuẩn bị xử lý song song nếu được yêu cầu
            if use_parallel:
                analysis_results = self._run_parallel_analysis(
                    df, analysis_type, analysis_results, file_id, filter_types, use_ml
                )
            else:
                analysis_results = self._run_sequential_analysis(
                    df, analysis_type, analysis_results, file_id, filter_types, use_ml
                )
            
            # Tính thời gian thực hiện tổng thể
            total_time = time.time() - start_time
            analysis_results["performance_metrics"]["total_execution_time"] = round(total_time, 3)
            
            logger.info(f"Analysis completed in {total_time:.3f} seconds")
            
            return analysis_results
                
        except Exception as e:
            logger.error(f"Error in run_analysis: {str(e)}", exc_info=True)
            
            import traceback
            stack_trace = traceback.format_exc()
            
            error_response = {
                "error": str(e),
                "traceback": stack_trace
            }
            
            if "analysis_results" in locals() and isinstance(analysis_results, dict):
                # Lọc các kết quả rỗng
                partial_results = {k: v for k, v in analysis_results.items() 
                                if v and (isinstance(v, dict) and len(v) > 0 or 
                                        isinstance(v, list) and len(v) > 0)}
                if partial_results:
                    error_response["partial_results"] = partial_results
            
            return error_response
    
    def _sample_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Lấy mẫu DataFrame theo cấu hình với nhiều phương pháp
        """
        max_rows = self.config.get("data_processing", {}).get("max_rows_analysis", 100000)
        sample_method = self.config.get("data_processing", {}).get("sample_method", "random")
        
        if len(df) <= max_rows:
            return df
            
        logger.info(f"Sampling dataframe from {len(df)} to {max_rows} rows using {sample_method} method")
        
        if sample_method == "random":
            return df.sample(max_rows, random_state=42)
        elif sample_method == "stratified":
            # Cố gắng lấy mẫu stratified nếu có cột categorical
            cat_cols = self.column_types.get("categorical", [])
            if cat_cols and len(cat_cols) > 0:
                strat_col = cat_cols[0]  # Chọn cột đầu tiên để stratify
                # Tính tỷ lệ
                frac = min(max_rows / len(df), 1.0)
                return df.groupby(strat_col, group_keys=False).apply(
                    lambda x: x.sample(frac=frac, random_state=42)
                ).reset_index(drop=True).head(max_rows)
            else:
                return df.sample(max_rows, random_state=42)
        elif sample_method == "systematic":
            # Chọn mẫu hệ thống
            step = max(1, len(df) // max_rows)
            return df.iloc[::step].head(max_rows)
        elif sample_method == "time_based" and any(is_datetime(df[col]) for col in df.columns):
            # Lấy mẫu dựa trên thời gian nếu có cột datetime
            dt_cols = self.column_types.get("datetime", [])
            if dt_cols and len(dt_cols) > 0:
                dt_col = dt_cols[0]
                # Sort by time and sample evenly
                df_sorted = df.sort_values(by=dt_col)
                step = max(1, len(df) // max_rows)
                return df_sorted.iloc[::step].head(max_rows)
            else:
                return df.sample(max_rows, random_state=42)
        else:
            # Default to random sampling
            return df.sample(max_rows, random_state=42)
    
    def _optimize_memory_usage(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        Tối ưu bộ nhớ sử dụng với nhiều mức độ tối ưu
        
        Args:
            df: DataFrame cần tối ưu
            
        Returns:
            Tuple[pd.DataFrame, Dict]: DataFrame đã tối ưu và thông tin tối ưu
        """
        memory_before = df.memory_usage(deep=True).sum() / (1024 * 1024)  # MB
        
        # Xác định mức độ tối ưu
        opt_level = self.config.get("data_processing", {}).get("memory_optimization_level", "high")
        
        if opt_level == "none":
            return df, {
                "before_mb": round(memory_before, 2),
                "after_mb": round(memory_before, 2),
                "reduction_percent": 0
            }
        
        # Tối ưu kiểu dữ liệu
        df_optimized = df.copy()
        
        # Sử dụng hàm utility để tối ưu với cấp độ phù hợp
        try:
            df_optimized = optimize_dataframe_memory(df_optimized)
        except ImportError:
            # Fallback nếu module không có sẵn
            # Tối ưu cột số nguyên
            int_columns = df.select_dtypes(include=['int']).columns
            for col in int_columns:
                col_min, col_max = df[col].min(), df[col].max()
                
                # Unsigned int
                if col_min >= 0:
                    if col_max < 255:
                        df_optimized[col] = df[col].astype(np.uint8)
                    elif col_max < 65535:
                        df_optimized[col] = df[col].astype(np.uint16)
                    elif col_max < 4294967295:
                        df_optimized[col] = df[col].astype(np.uint32)
                # Signed int
                else:
                    if col_min > -128 and col_max < 127:
                        df_optimized[col] = df[col].astype(np.int8)
                    elif col_min > -32768 and col_max < 32767:
                        df_optimized[col] = df[col].astype(np.int16)
                    elif col_min > -2147483648 and col_max < 2147483647:
                        df_optimized[col] = df[col].astype(np.int32)
            
            # Tối ưu cột float
            float_columns = df.select_dtypes(include=['float']).columns
            for col in float_columns:
                df_optimized[col] = df[col].astype(np.float32)
            
            # Tối ưu cột categorical
            object_columns = df.select_dtypes(include=['object']).columns
            for col in object_columns:
                num_unique = df[col].nunique()
                if num_unique <= min(100, len(df) * 0.1):
                    df_optimized[col] = df[col].astype('category')
        
        memory_after = df_optimized.memory_usage(deep=True).sum() / (1024 * 1024)  # MB
        
        # Lưu thông tin tối ưu
        self.memory_tracker = {
            "initial": memory_before,
            "optimized": memory_after,
            "reduction": memory_before - memory_after
        }
        
        return df_optimized, {
            "before_mb": round(memory_before, 2),
            "after_mb": round(memory_after, 2),
            "reduction_percent": round((memory_before - memory_after) / memory_before * 100, 2),
            "optimization_level": opt_level
        }
    
    def _run_parallel_analysis(self, df: pd.DataFrame, analysis_type: str, 
                             analysis_results: Dict, file_id: Optional[str] = None,
                             filter_types: Optional[List[str]] = None, 
                             use_ml: bool = False) -> Dict:
        """
        Chạy phân tích song song với ThreadPoolExecutor
        """
        import concurrent.futures
        
        # Số workers tối đa
        max_workers = min(8, (os.cpu_count() or 4))
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        futures = {}
        
        try:
            # Phân tích chất lượng dữ liệu
            if analysis_type in ["full", "quality"]:
                logger.info("Running data quality assessment")
                quality_start = time.time()
                futures["quality"] = executor.submit(self.data_validator.validate_dataset, df)
            
            # Xử lý dữ liệu để phân tích
            logger.info("Processing data for analysis")
            process_start = time.time()
            df_processed = self.data_processor.process(df)
            analysis_results["performance_metrics"]["data_processing_time"] = round(time.time() - process_start, 3)
            
            # Phân tích thống kê
            if analysis_type in ["full", "statistics"]:
                logger.info("Running statistical analysis")
                stats_start = time.time()
                futures["statistics"] = executor.submit(self._run_statistical_analysis, df_processed)
            
            # Phân tích nâng cao
            if analysis_type in ["full", "advanced"]:
                logger.info("Running advanced analysis")
                advanced_start = time.time()
                futures["advanced"] = executor.submit(self._run_advanced_analysis, df_processed)
            
            # Phân tích chuỗi thời gian (nếu có cột datetime)
            has_datetime = any(is_datetime(df_processed[col]) for col in df_processed.columns)
            
            if analysis_type in ["full", "time_series"] and has_datetime:
                logger.info("Running time series analysis")
                timeseries_start = time.time()
                futures["time_series"] = executor.submit(self._run_time_series_analysis, df_processed)
            
            # Thu thập kết quả từ các tác vụ song song
            if "quality" in futures:
                quality_report = futures["quality"].result()
                quality_end_time = time.time()
                analysis_results["data_quality"] = quality_report
                analysis_results["recommendations"].extend(quality_report.get("recommendations", []))
                analysis_results["performance_metrics"]["quality_assessment_time"] = round(quality_end_time - quality_start, 3)
            
            if "statistics" in futures:
                stats_result = futures["statistics"].result()
                stats_end_time = time.time()
                analysis_results["statistical_analysis"] = stats_result
                analysis_results["performance_metrics"]["statistical_analysis_time"] = round(stats_end_time - stats_start, 3)
            
            if "advanced" in futures:
                advanced_result = futures["advanced"].result()
                advanced_end_time = time.time()
                analysis_results["advanced_analysis"] = advanced_result
                analysis_results["performance_metrics"]["advanced_analysis_time"] = round(advanced_end_time - advanced_start, 3)
            
            if "time_series" in futures:
                ts_result = futures["time_series"].result()
                ts_end_time = time.time()
                analysis_results["time_series_analysis"] = ts_result
                analysis_results["performance_metrics"]["time_series_analysis_time"] = round(ts_end_time - timeseries_start, 3)
            
            # Tạo insights và visualizations
            if analysis_type in ["full", "insights", "visualizations"]:
                # Sử dụng một thread pool riêng cho phần này
                viz_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
                viz_futures = {}
                
                if analysis_type in ["full", "insights"]:
                    logger.info("Generating insights")
                    insights_start = time.time()
                    viz_futures["insights"] = viz_executor.submit(
                        self._generate_insights, df_processed, file_id, filter_types, use_ml
                    )
                
                if analysis_type in ["full", "visualizations"]:
                    logger.info("Generating visualizations")
                    viz_start = time.time()
                    viz_futures["visualizations"] = viz_executor.submit(
                        self._generate_visualizations, df_processed, file_id, filter_types
                    )
                
                # Thu thập kết quả
                if "insights" in viz_futures:
                    insights = viz_futures["insights"].result()
                    insights_end_time = time.time()
                    analysis_results["insights"] = insights
                    analysis_results["performance_metrics"]["insights_generation_time"] = round(insights_end_time - insights_start, 3)
                
                if "visualizations" in viz_futures:
                    visualizations = viz_futures["visualizations"].result()
                    viz_end_time = time.time()
                    analysis_results["visualizations"] = visualizations
                    analysis_results["performance_metrics"]["visualizations_generation_time"] = round(viz_end_time - viz_start, 3)
                
                viz_executor.shutdown()
            
            # Thêm khuyến nghị từ phân tích nâng cao
            if analysis_type in ["full", "advanced"]:
                advanced_recommendations = self._generate_advanced_recommendations(df_processed)
                analysis_results["recommendations"].extend(advanced_recommendations)
            
            # Thêm khuyến nghị phân tích
            analysis_results["recommendations"].extend(self._generate_analysis_recommendations(df_processed))
            
            # Loại bỏ khuyến nghị trùng lặp
            if analysis_results["recommendations"]:
                analysis_results["recommendations"] = list(dict.fromkeys(analysis_results["recommendations"]))
            
            return analysis_results
        
        finally:
            executor.shutdown()
    
    def _run_sequential_analysis(self, df: pd.DataFrame, analysis_type: str, 
                               analysis_results: Dict, file_id: Optional[str] = None,
                               filter_types: Optional[List[str]] = None, 
                               use_ml: bool = False) -> Dict:
        """
        Chạy phân tích tuần tự
        """
        # Phân tích chất lượng dữ liệu
        if analysis_type in ["full", "quality"]:
            logger.info("Running data quality assessment")
            quality_start = time.time()
            quality_report = self.data_validator.validate_dataset(df)
            analysis_results["data_quality"] = quality_report
            analysis_results["recommendations"].extend(quality_report.get("recommendations", []))
            analysis_results["performance_metrics"]["quality_assessment_time"] = round(time.time() - quality_start, 3)
        
        # Xử lý dữ liệu để phân tích
        logger.info("Processing data for analysis")
        process_start = time.time()
        df_processed = self.data_processor.process(df)
        analysis_results["performance_metrics"]["data_processing_time"] = round(time.time() - process_start, 3)
        
        # Phân tích thống kê
        if analysis_type in ["full", "statistics"]:
            logger.info("Running statistical analysis")
            stats_start = time.time()
            analysis_results["statistical_analysis"] = self._run_statistical_analysis(df_processed)
            analysis_results["performance_metrics"]["statistical_analysis_time"] = round(time.time() - stats_start, 3)
        
        # Phân tích nâng cao
        if analysis_type in ["full", "advanced"]:
            logger.info("Running advanced analysis")
            advanced_start = time.time()
            analysis_results["advanced_analysis"] = self._run_advanced_analysis(df_processed)
            analysis_results["performance_metrics"]["advanced_analysis_time"] = round(time.time() - advanced_start, 3)
        
        # Phân tích chuỗi thời gian (nếu có cột datetime)
        has_datetime = any(is_datetime(df_processed[col]) for col in df_processed.columns)
        
        if analysis_type in ["full", "time_series"] and has_datetime:
            logger.info("Running time series analysis")
            timeseries_start = time.time()
            analysis_results["time_series_analysis"] = self._run_time_series_analysis(df_processed)
            analysis_results["performance_metrics"]["time_series_analysis_time"] = round(time.time() - timeseries_start, 3)
        
        # Tạo insights
        if analysis_type in ["full", "insights"]:
            logger.info("Generating insights")
            insights_start = time.time()
            analysis_results["insights"] = self._generate_insights(df_processed, file_id, filter_types, use_ml)
            analysis_results["performance_metrics"]["insights_generation_time"] = round(time.time() - insights_start, 3)
        
        # Tạo visualizations
        if analysis_type in ["full", "visualizations"]:
            logger.info("Generating visualizations")
            viz_start = time.time()
            analysis_results["visualizations"] = self._generate_visualizations(df_processed, file_id, filter_types)
            analysis_results["performance_metrics"]["visualizations_generation_time"] = round(time.time() - viz_start, 3)
        
        # Thêm khuyến nghị từ phân tích nâng cao
        if analysis_type in ["full", "advanced"]:
            advanced_recommendations = self._generate_advanced_recommendations(df_processed)
            analysis_results["recommendations"].extend(advanced_recommendations)
        
        # Thêm khuyến nghị phân tích
        analysis_results["recommendations"].extend(self._generate_analysis_recommendations(df_processed))
        
        # Loại bỏ khuyến nghị trùng lặp
        if analysis_results["recommendations"]:
            analysis_results["recommendations"] = list(dict.fromkeys(analysis_results["recommendations"]))
        
        return analysis_results
    
    def _generate_insights(self, df: pd.DataFrame, file_id: Optional[str], 
                         filter_types: Optional[List[str]], use_ml: bool) -> List[Dict]:
        """Generate insights from the data"""
        if use_ml:
            # Use ML-based insights (Mistral) - slower but more contextual
            insights = self.insight_generator.generate_insights(df, self.config, file_id, filter_types)
        else:
            # Use rule-based insights - faster performance
            insights = self.insight_generator.generate_rule_based_insights(df, file_id, filter_types)
        
        return [insight.model_dump() for insight in insights]
    
    def _generate_visualizations(self, df: pd.DataFrame, file_id: Optional[str], 
                               filter_types: Optional[List[str]]) -> List[Dict]:
        """Generate visualizations from the data"""
        visualizations = self.chart_generator.generate_automatic_charts(df, file_id, filter_types)
        return [viz.model_dump() for viz in visualizations]
    
    def _detect_column_types(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Auto detect column types using DataProcessor"""
        return self.data_processor.get_column_types(df)
    
    def _analyze_dataset_info(self, df: pd.DataFrame) -> Dict:
        """Phân tích thông tin cơ bản về dataset với phát hiện datetime nâng cao"""
        try:
            logger.info("Analyzing basic dataset properties")
            num_rows, num_cols = df.shape
            memory_usage = df.memory_usage(deep=True).sum() / (1024 * 1024)

            if not hasattr(self, 'column_types') or not self.column_types:
                self.column_types = self.data_processor.get_column_types(df)

            # Thêm thông tin về kiểu dữ liệu
            dtype_info = {}
            for dtype, count in df.dtypes.astype(str).value_counts().to_dict().items():
                dtype_info[dtype] = {
                    "count": count,
                    "percent": round(100 * count / num_cols, 1)
                }

            # Tính thông tin về missing values
            missing_values = df.isna().sum()
            total_missing = missing_values.sum()
            missing_percent = total_missing / (num_rows * num_cols) * 100
            
            # Phát hiện dữ liệu thời gian và bổ sung thông tin chi tiết
            time_range = None
            time_insights = {}
            datetime_cols = self.column_types["datetime"]
            
            if datetime_cols:
                # Chọn cột datetime có ít missing values nhất để phân tích
                missing_counts = {col: df[col].isna().sum() for col in datetime_cols}
                if missing_counts:
                    primary_datetime_col = min(missing_counts.items(), key=lambda x: x[1])[0]
                    try:
                        # Chuyển đổi sang datetime nếu cần
                        if not is_datetime(df[primary_datetime_col]):
                            datetime_series = convert_to_datetime(df[primary_datetime_col])
                        else:
                            datetime_series = df[primary_datetime_col]
                        
                        # Lấy min/max date
                        min_date = datetime_series.min()
                        max_date = datetime_series.max()
                        
                        if not pd.isna(min_date) and not pd.isna(max_date):
                            time_range = f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
                            
                            # Phân tích phân phối thời gian nếu có ít nhất 10 giá trị
                            if datetime_series.count() >= 10:
                                try:
                                    distribution = analyze_datetime_distribution(datetime_series)
                                    time_insights = {
                                        "range_days": distribution.get("range_days", 0),
                                        "suggested_frequency": distribution.get("suggested_frequency", "unknown"),
                                        "top_years": dict(sorted(distribution.get("distributions", {}).get("year", {}).items(), 
                                                                key=lambda x: x[1], reverse=True)[:3]),
                                        "seasonality": distribution.get("seasonality", {"detected": False})
                                    }
                                except Exception as e:
                                    logger.warning(f"Error analyzing datetime distribution: {str(e)}")
                    except Exception as e:
                        logger.warning(f"Error processing datetime column: {str(e)}")
            
            # Tổng hợp các loại cột theo thể loại
            column_type_summary = {
                col_type: len(cols) for col_type, cols in self.column_types.items() if cols
            }
            
            # Phát hiện và phân tích các cột duplicate
            duplicate_cols = self._detect_duplicate_columns(df)
            
            result = {
                "rows": num_rows,
                "columns": num_cols,
                "memory_usage_mb": round(memory_usage, 2),
                "dtypes_summary": dtype_info,
                "column_types": self.column_types,
                "column_type_counts": column_type_summary,
                "time_range": time_range,
                "missing_values": {
                    "count": int(total_missing),
                    "percent": float(missing_percent),
                    "columns_with_missing": len(missing_values[missing_values > 0])
                },
                "duplicate_columns": duplicate_cols
            }
            
            # Thêm thông tin phong phú về datetime nếu có
            if time_insights:
                result["time_insights"] = time_insights
        
            return result
        except Exception as e:
            logger.error(f"Error analyzing dataset info: {str(e)}")
            return {"error": str(e)}
    
    def _detect_duplicate_columns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Phát hiện các cột trùng lặp trong dataset
        
        Args:
            df: DataFrame cần kiểm tra
                
        Returns:
            Dict: Thông tin về các cột trùng lặp
        """
        dup_cols = self.data_processor.detect_duplicate_columns(df)
        
        if not dup_cols:
            return {"has_duplicates": False, "duplicate_count": 0}
        
        return {
            "has_duplicates": True,
            "duplicate_count": len(dup_cols),
            "duplicates": {dup: original for dup, original in dup_cols.items()}
        }
    
    def _run_statistical_analysis(self, df: pd.DataFrame) -> Dict:
        """Phân tích thống kê chi tiết về dataset, cải tiến để xử lý nhiều kiểu dữ liệu"""
        try:
            statistics = {
                "numeric_summary": {},
                "categorical_summary": {},
                "datetime_summary": {},
                "correlation_matrix": {},
                "group_statistics": [],
                "distribution_stats": {},
                "binary_summary": {},
                "gender_summary": {},
                "likert_summary": {},
                "range_summary": {},
                "text_summary": {}
            }
            
            # Tạo bản sao DataFrame để xử lý
            df_processed = df.copy()
            
            # Sử dụng column_types đã được phát hiện từ run_analysis
            if not hasattr(self, 'column_types') or not self.column_types:
                self.column_types = self.data_processor.get_column_types(df)
            
            # Chuyển đổi kiểu dữ liệu an toàn
            def safe_convert_to_numeric(series):
                try:
                    # Loại bỏ các ký tự không phải số
                    series = series.astype(str).str.replace(',', '.').str.replace(' ', '')
                    # Thử chuyển đổi
                    return pd.to_numeric(series, errors='coerce')
                except:
                    return pd.Series([np.nan] * len(series))
            
            # Chỉ chuyển đổi các cột numeric cần thiết
            numeric_cols_need_convert = []
            for col in self.column_types["numeric"]:
                if col in df_processed.columns and not is_numeric_dtype(df_processed[col]):
                    numeric_cols_need_convert.append(col)
            
            for col in numeric_cols_need_convert:
                converted = safe_convert_to_numeric(df_processed[col])
                if converted.notna().sum() / len(converted) > 0.5:
                    df_processed[col] = converted
            
            # Lấy danh sách cột theo loại
            numeric_cols = self.column_types.get("numeric", [])
            categorical_cols = self.column_types.get("categorical", [])
            datetime_cols = self.column_types.get("datetime", [])

            # Thống kê numeric
            if numeric_cols:
                desc_stats = df_processed[numeric_cols].describe(percentiles=[.01, .05, .25, .5, .75, .95, .99]).round(2)
                statistics["numeric_summary"] = desc_stats.to_dict()
                
                # Thêm phân tích phân phối chi tiết hơn
                for col in numeric_cols:
                    valid_values = df_processed[col].dropna()
                    if len(valid_values) > 0:
                        try:
                            # Thống kê cơ bản
                            skewness = float(stats.skew(valid_values))
                            kurtosis = float(stats.kurtosis(valid_values))
                            
                            statistics["numeric_summary"][col]["skewness"] = skewness
                            statistics["numeric_summary"][col]["kurtosis"] = kurtosis
                            
                            # Chi tiết phân phối
                            hist_counts, hist_bins = np.histogram(valid_values, bins='auto')
                            
                            statistics["distribution_stats"][col] = {
                                "histogram": {
                                    "counts": hist_counts.tolist(),
                                    "bins": hist_bins.tolist()
                                },
                                "distribution": {
                                    "skewness": skewness,
                                    "kurtosis": kurtosis,
                                    "distribution_type": self._detect_distribution_type(valid_values)
                                }
                            }
                        except Exception as skew_err:
                            logger.warning(f"Error calculating distribution for {col}: {skew_err}")
            
            # Phân tích cho Likert scale
            likert_cols = self.column_types.get("likert", [])
            if likert_cols:
                for col in likert_cols:
                    valid_values = df_processed[col].dropna()
                    if len(valid_values) > 0:
                        try:
                            # Thống kê cơ bản
                            statistics["likert_summary"][col] = {
                                "mean": float(valid_values.mean()),
                                "median": float(valid_values.median()),
                                "mode": float(valid_values.mode().iloc[0]) if not valid_values.mode().empty else None,
                                "std": float(valid_values.std()),
                                "min": float(valid_values.min()),
                                "max": float(valid_values.max()),
                                "scale_points": sorted(valid_values.unique().tolist()),
                                "value_counts": valid_values.value_counts().to_dict(),
                                "percent_distribution": {
                                    str(k): float(v / len(valid_values) * 100) 
                                    for k, v in valid_values.value_counts().items()
                                }
                            }
                        except Exception as e:
                            logger.warning(f"Error analyzing Likert scale column {col}: {str(e)}")

            # Phân tích cho các cột Binary
            binary_cols = self.column_types.get("binary", [])
            if binary_cols:
                for col in binary_cols:
                    try:
                        value_counts = df_processed[col].value_counts()
                        statistics["binary_summary"][col] = {
                            "value_counts": value_counts.to_dict(),
                            "percent_distribution": {
                                str(k): float(v / len(df_processed) * 100) 
                                for k, v in value_counts.items()
                            },
                            "mode": df_processed[col].mode().iloc[0] if not df_processed[col].mode().empty else None
                        }
                    except Exception as e:
                        logger.warning(f"Error analyzing binary column {col}: {str(e)}")

            # Phân tích cho các cột Gender
            gender_cols = self.column_types.get("gender", [])
            if gender_cols:
                for col in gender_cols:
                    try:
                        value_counts = df_processed[col].value_counts()
                        statistics["gender_summary"][col] = {
                            "value_counts": value_counts.to_dict(),
                            "percent_distribution": {
                                str(k): float(v / len(df_processed) * 100) 
                                for k, v in value_counts.items()
                            }
                        }
                    except Exception as e:
                        logger.warning(f"Error analyzing gender column {col}: {str(e)}")

            # Phân tích cho các cột Range
            range_cols = self.column_types.get("range", [])
            if range_cols:
                for col in range_cols:
                    try:
                        df_processed[col] = df_processed[col].astype(str)
                        
                        # Tìm min-max ranges bằng regex
                        range_pattern = r'(\d+)\s*[-–—]\s*(\d+)'
                        ranges = df_processed[col].str.extract(range_pattern)
                        
                        if not ranges.empty and not ranges.iloc[:, 0].empty and not ranges.iloc[:, 1].empty:
                            min_vals = pd.to_numeric(ranges.iloc[:, 0], errors='coerce')
                            max_vals = pd.to_numeric(ranges.iloc[:, 1], errors='coerce')
                            
                            statistics["range_summary"][col] = {
                                "unique_count": df_processed[col].nunique(),
                                "average_min": float(min_vals.mean()) if not min_vals.empty else None,
                                "average_max": float(max_vals.mean()) if not max_vals.empty else None,
                                "average_range": float((max_vals - min_vals).mean()) if not min_vals.empty and not max_vals.empty else None,
                                "missing_count": df_processed[col].isna().sum(),
                                "top_ranges": df_processed[col].value_counts().head(5).to_dict()
                            }
                        else:
                            statistics["range_summary"][col] = {
                                "unique_count": df_processed[col].nunique(),
                                "missing_count": df_processed[col].isna().sum(),
                                "top_values": df_processed[col].value_counts().head(5).to_dict()
                            }
                    except Exception as e:
                        logger.warning(f"Error analyzing range column {col}: {str(e)}")

            # Phân tích cho các cột Text
            text_cols = self.column_types.get("text", [])
            if text_cols:
                for col in text_cols:
                    try:
                        df_processed[col] = df_processed[col].astype(str)
                        
                        text_lengths = df_processed[col].str.len()
                        word_counts = df_processed[col].str.split().str.len()
                        
                        statistics["text_summary"][col] = {
                            "unique_count": df_processed[col].nunique(),
                            "average_length": float(text_lengths.mean()),
                            "average_words": float(word_counts.mean()),
                            "max_length": int(text_lengths.max()),
                            "min_length": int(text_lengths.min()),
                            "missing_count": df_processed[col].isna().sum()
                        }
                    except Exception as e:
                        logger.warning(f"Error analyzing text column {col}: {str(e)}")

            # Thống kê categorical
            if categorical_cols:
                for col in categorical_cols:
                    # Xử lý an toàn khi có các giá trị không phải string
                    value_counts = df_processed[col].astype(str).value_counts().head(15).to_dict()  # Tăng số lượng giá trị top
                    unique_count = df_processed[col].astype(str).nunique()
                    
                    # Thêm tỷ lệ top values
                    top_values_pct = {}
                    for val, count in value_counts.items():
                        top_values_pct[str(val)] = float(count / len(df_processed) * 100)
                    
                    # Thêm entropie để đo lường sự tập trung
                    try:
                        entropy = stats.entropy(df_processed[col].astype(str).value_counts()) if unique_count > 1 else 0
                    except:
                        entropy = 0
                    
                    statistics["categorical_summary"][col] = {
                        "unique_values": unique_count,
                        "top_values": value_counts,
                        "top_values_percent": top_values_pct,
                        "mode": df_processed[col].astype(str).mode().iloc[0] if not df_processed[col].mode().empty else None,
                        "entropy": float(entropy)
                    }
            
            if datetime_cols:
                for col in datetime_cols:
                    try:
                        # Chuyển đổi sang datetime nếu chưa phải
                        datetime_series = convert_to_datetime(df_processed[col])
                        valid_dates = datetime_series.dropna()
                        
                        if len(valid_dates) > 0:
                            date_range = (valid_dates.max() - valid_dates.min()).total_seconds() / (60 * 60 * 24)  # days
                            
                            statistics["datetime_summary"][col] = {
                                "min": valid_dates.min().isoformat(),
                                "max": valid_dates.max().isoformat(),
                                "range_days": float(date_range)
                            }
                            
                            try:
                                # Phân phối theo năm, tháng, thứ và giờ
                                year_counts = valid_dates.dt.year.value_counts().to_dict()
                                month_counts = valid_dates.dt.month.value_counts().to_dict()
                                day_of_week_counts = valid_dates.dt.dayofweek.value_counts().to_dict()
                                
                                # Thêm giờ trong ngày nếu có thông tin
                                hour_distribution = {}
                                if hasattr(valid_dates.dt, 'hour'):
                                    hour_distribution = valid_dates.dt.hour.value_counts().to_dict()
                                
                                statistics["datetime_summary"][col]["year_distribution"] = {str(k): int(v) for k, v in year_counts.items()}
                                statistics["datetime_summary"][col]["month_distribution"] = {str(k): int(v) for k, v in month_counts.items()}
                                statistics["datetime_summary"][col]["day_of_week_distribution"] = {str(k): int(v) for k, v in day_of_week_counts.items()}
                                
                                if hour_distribution:
                                    statistics["datetime_summary"][col]["hour_distribution"] = {str(k): int(v) for k, v in hour_distribution.items()}
                                
                                # Phân tích khoảng cách thời gian
                                try:
                                    sorted_dates = valid_dates.sort_values()
                                    time_diffs = sorted_dates.diff().dropna()
                                    
                                    if len(time_diffs) > 0:
                                        # Chuyển đổi sang seconds
                                        time_diffs_seconds = time_diffs.dt.total_seconds()
                                        
                                        statistics["datetime_summary"][col]["time_intervals"] = {
                                            "min_interval_seconds": float(time_diffs_seconds.min()),
                                            "max_interval_seconds": float(time_diffs_seconds.max()),
                                            "median_interval_seconds": float(time_diffs_seconds.median()),
                                            "mean_interval_seconds": float(time_diffs_seconds.mean()),
                                            "std_interval_seconds": float(time_diffs_seconds.std())
                                        }
                                except Exception as interval_err:
                                    logger.warning(f"Error calculating time intervals for {col}: {interval_err}")
                            except Exception as date_err:
                                logger.warning(f"Error processing datetime details for {col}: {date_err}")
                    except Exception as conv_err:
                        logger.warning(f"Error converting datetime column {col}: {conv_err}")
            
            # Ma trận tương quan - sử dụng numeric_cols đã xác định và thêm tính năng phát hiện non-linear
            if len(numeric_cols) > 1:
                try:
                    # Pearson correlation - linear
                    corr_matrix = df_processed[numeric_cols].corr(method='pearson').round(2)
                    
                    # Thêm Spearman correlation - non-linear, rank-based
                    spearman_corr = df_processed[numeric_cols].corr(method='spearman').round(2)
                    
                    correlation_data = []
                    for i, col1 in enumerate(corr_matrix.columns):
                        for j, col2 in enumerate(corr_matrix.columns):
                            if i < j:  # Chỉ lấy nửa trên của ma trận
                                # Linear vs Non-linear assessment
                                pearson_corr = float(corr_matrix.loc[col1, col2])
                                spearman_corr_val = float(spearman_corr.loc[col1, col2])
                                
                                # Kiểm tra mối quan hệ phi tuyến
                                is_nonlinear = abs(spearman_corr_val) > abs(pearson_corr) + 0.2
                                
                                correlation_data.append({
                                    "column1": col1,
                                    "column2": col2,
                                    "pearson_correlation": pearson_corr,
                                    "spearman_correlation": spearman_corr_val,
                                    "relationship_type": "non_linear" if is_nonlinear else "linear",
                                    "strength": self._get_correlation_strength(max(abs(pearson_corr), abs(spearman_corr_val)))
                                })
                    
                    correlation_data = sorted(correlation_data, key=lambda x: max(abs(x["pearson_correlation"]), abs(x["spearman_correlation"])), reverse=True)
                    statistics["correlation_matrix"]["correlations"] = correlation_data[:20]  # Chỉ lấy top 20
                    
                    # Thêm tổng kết về tương quan
                    high_correlations = [corr for corr in correlation_data if corr["strength"] == "strong"]
                    statistics["correlation_matrix"]["summary"] = {
                        "strong_correlations_count": len(high_correlations),
                        "top_correlation": correlation_data[0] if correlation_data else None,
                        "avg_correlation": float(np.mean([max(abs(corr["pearson_correlation"]), abs(corr["spearman_correlation"])) for corr in correlation_data])) if correlation_data else 0
                    }
                except Exception as corr_err:
                    logger.warning(f"Error calculating correlation matrix: {corr_err}")
            
            # Thống kê theo nhóm - chỉ sử dụng categorical_cols đã xác định
            if categorical_cols and numeric_cols:
                # Chọn categorical và numeric columns cho group by
                for cat_col in categorical_cols[:2]:  # Giới hạn 2 cột categorical đầu tiên
                    if df_processed[cat_col].nunique() <= 10:  # Chỉ dùng nếu số nhóm hợp lý
                        for num_col in numeric_cols[:3]:  # Giới hạn 3 cột numeric đầu tiên
                            try:
                                # Thêm thống kê chi tiết hơn như percentiles
                                group_stats = df_processed.groupby(cat_col, observed=True)[num_col].agg([
                                    'mean', 'median', 'std', 'min', 'max', 'count',
                                    lambda x: x.quantile(0.25).round(2),
                                    lambda x: x.quantile(0.75).round(2)
                                ]).reset_index()
                                
                                # Đổi tên cho lambda functions
                                group_stats = group_stats.rename(columns={
                                    '<lambda_0>': 'q1',
                                    '<lambda_1>': 'q3'
                                })
                                
                                # Tính ANOVA để kiểm tra sự khác biệt giữa các nhóm
                                try:
                                    groups = [df_processed[df_processed[cat_col] == val][num_col].dropna() 
                                            for val in df_processed[cat_col].unique()]
                                    groups = [group for group in groups if len(group) > 0]
                                    
                                    valid_groups = []
                                    for group in groups:
                                        if len(group) > 0 and group.var() > 0:
                                            valid_groups.append(group)

                                    if len(valid_groups) >= 2:
                                        f_val, p_val = stats.f_oneway(*valid_groups)
                                        
                                        statistics["group_statistics"].append({
                                            "group_by": cat_col,
                                            "value_column": num_col,
                                            "stats": group_stats.to_dict(orient='records'),
                                            "anova": {
                                                "f_value": float(f_val),
                                                "p_value": float(p_val),
                                                "significant_difference": bool(p_val < 0.05)
                                            }
                                        })
                                    else:
                                        statistics["group_statistics"].append({
                                            "group_by": cat_col,
                                            "value_column": num_col,
                                            "stats": group_stats.to_dict(orient='records'),
                                            "anova": {
                                                "error": "Insufficient valid groups for ANOVA test"
                                            }
                                        })
                                except Exception as anova_err:
                                    statistics["group_statistics"].append({
                                        "group_by": cat_col,
                                        "value_column": num_col,
                                        "stats": group_stats.to_dict(orient='records'),
                                        "anova": {
                                            "error": str(anova_err)
                                        }
                                    })
                            except Exception as group_err:
                                logger.warning(f"Error calculating group statistics for {cat_col} and {num_col}: {group_err}")
            
            return statistics
        except Exception as e:
            logger.error(f"Error running statistical analysis: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    def _detect_distribution_type(self, data: pd.Series) -> str:
        """
        Phát hiện kiểu phân phối của dữ liệu
        
        Args:
            data: Series cần phân tích
            
        Returns:
            str: Kiểu phân phối
        """
        try:
            # Kiểm tra phân phối chuẩn
            _, norm_p = stats.normaltest(data)
            
            # Kiểm tra các kiểu phân phối khác
            # Phân phối log-normal
            try:
                # Loại bỏ giá trị <= 0
                pos_data = data[data > 0]
                if len(pos_data) > 0.8 * len(data):  # Nếu hầu hết giá trị > 0
                    _, lognorm_p = stats.normaltest(np.log(pos_data))
                else:
                    lognorm_p = 0
            except:
                lognorm_p = 0
            
            # Phân phối đều (Uniform)
            try:
                _, uniform_p = stats.kstest(data, 'uniform', args=(data.min(), data.max() - data.min()))
            except:
                uniform_p = 0
            
            # Quyết định kiểu phân phối
            if norm_p > 0.05:
                return "normal"
            elif lognorm_p > 0.05:
                return "log_normal"
            elif uniform_p > 0.05:
                return "uniform"
            elif abs(stats.skew(data)) > 1:
                return "skewed"
            elif stats.kurtosis(data) > 1:
                return "heavy_tailed"
            else:
                return "unknown"
        except Exception as e:
            logger.warning(f"Error detecting distribution: {str(e)}")
            return "unknown"
    
    def _get_correlation_strength(self, corr_val: float) -> str:
        """
        Xác định độ mạnh của tương quan
        
        Args:
            corr_val: Giá trị tương quan (đã lấy giá trị tuyệt đối)
            
        Returns:
            str: Độ mạnh của tương quan
        """
        if corr_val >= 0.7:
            return "strong"
        elif corr_val >= 0.4:
            return "moderate"
        elif corr_val >= 0.2:
            return "weak"
        else:
            return "negligible"
            
    def _run_advanced_analysis(self, df: pd.DataFrame) -> Dict:
        """
        Chạy phân tích nâng cao với các phương pháp machine learning
        
        Args:
            df: DataFrame đã xử lý
            
        Returns:
            Dict: Kết quả phân tích nâng cao
        """
        try:
            advanced_results = {
                "performance_analysis": {},
                "dimensionality_reduction": {},
                "feature_importance": {},
                "clustering": {},
                "outlier_analysis": {},
                "text_analysis": {},
                "likert_analysis": {},
                "binary_patterns": {},
                "range_analysis": {},
                "gender_distribution": {}
            }
            
            # 1. Phân tích hiệu suất (bottlenecks)
            try:
                advanced_results["performance_analysis"] = self.data_processor.identify_performance_bottlenecks(df)
            except Exception as e:
                logger.error(f"Error in performance analysis: {str(e)}")
                advanced_results["performance_analysis"] = {"error": str(e)}
            
            # 2. Giảm chiều dữ liệu (PCA) với visualization
            numeric_cols = self.column_types.get("numeric", [])
            likert_cols = self.column_types.get("likert", [])
            binary_cols = self.column_types.get("binary", [])
            text_cols = self.column_types.get("text", [])
            range_cols = self.column_types.get("range", [])
            gender_cols = self.column_types.get("gender", [])

            all_numeric_cols = numeric_cols + likert_cols
            
            if len(all_numeric_cols) >= 3:
                try:
                    pca_df, component_info = self.data_processor.apply_pca(df, all_numeric_cols)
                    
                    # Tạo biểu diễn trực quan 2D
                    if len(component_info.get("components", {})) >= 2:
                        # Get first two components
                        pc1 = list(component_info["components"].keys())[0]
                        pc2 = list(component_info["components"].keys())[1]
                        
                        # Tạo dữ liệu biểu đồ
                        plot_data = pca_df[[pc1, pc2]].iloc[:min(1000, len(pca_df))].to_dict(orient='records')
                        
                        component_info["visualization"] = {
                            "type": "scatter",
                            "data": plot_data,
                            "x_axis": pc1,
                            "y_axis": pc2,
                            "title": "PCA Visualization (Top 2 Components)"
                        }
                    
                    advanced_results["dimensionality_reduction"] = {
                        "method": "PCA",
                        "components": component_info,
                        "pca_data_sample": pca_df.head(5).to_dict(orient='records')
                    }
                except Exception as e:
                    logger.error(f"Error in PCA analysis: {str(e)}")
                    advanced_results["dimensionality_reduction"] = {"error": str(e)}
            
            # 3. Feature importance với multiple methods - mở rộng để bao gồm các cột phù hợp
            try:
                feature_importance_method = self.config.get("ml", {}).get("feature_importance_method", "pca")
                important_features = {}
                importance_scores = {}
                
                # Numeric columns including numeric and likert-type columns
                numeric_cols = self.column_types.get("numeric", [])
                likert_cols = self.column_types.get("likert", [])
                all_numeric_cols = numeric_cols + likert_cols
                
                if feature_importance_method == "shap" and len(df) >= 100 and len(all_numeric_cols) >= 2:
                    try:
                        from sklearn.ensemble import RandomForestRegressor
                        import numpy as np
                        
                        # Select a target column (first numeric column)
                        target_col = all_numeric_cols[0]
                        feature_cols = [col for col in all_numeric_cols if col != target_col]
                        
                        if feature_cols:
                            # Prepare data
                            X = df[feature_cols].fillna(df[feature_cols].median())
                            y = df[target_col].fillna(df[target_col].median())
                            
                            # Train Random Forest model
                            model = RandomForestRegressor(n_estimators=50, random_state=42)
                            model.fit(X, y)
                            
                            # Get feature importances
                            importances = model.feature_importances_
                            
                            # Create importance dictionary
                            importance_dict = {
                                feature_cols[i]: float(importances[i]) 
                                for i in range(len(feature_cols))
                            }
                            
                            # Sort by importance
                            sorted_importances = dict(
                                sorted(
                                    importance_dict.items(), 
                                    key=lambda x: x[1], 
                                    reverse=True
                                )
                            )
                            
                            # Normalize to sum to 1
                            total = sum(sorted_importances.values())
                            if total > 0:
                                normalized_importances = {
                                    k: v/total for k, v in sorted_importances.items()
                                }
                            else:
                                normalized_importances = sorted_importances
                            
                            important_features = list(normalized_importances.keys())[:10]
                            importance_scores = normalized_importances
                            
                    except Exception as shap_err:
                        logger.warning(f"Error in SHAP feature importance: {str(shap_err)}")
                
                # Fallback to PCA-based importance if SHAP fails or not used
                if not important_features:
                    try:
                        # Use DataProcessor's select_important_features method
                        important_features = self.data_processor.select_important_features(
                            df, 
                            max_features=10
                        )
                        
                        # Create importance scores based on ranking
                        importance_scores = {
                            feature: (len(important_features) - i) / len(important_features)
                            for i, feature in enumerate(important_features)
                        }
                    except Exception as pca_err:
                        logger.error(f"Error in PCA feature importance: {str(pca_err)}")
                        important_features = []
                        importance_scores = {}
                
                # Prepare final results
                advanced_results["feature_importance"] = {
                    "method": feature_importance_method,
                    "important_features": important_features,
                    "importance_scores": importance_scores
                }
            
            except Exception as e:
                logger.error(f"Error in feature importance analysis: {str(e)}")
                advanced_results["feature_importance"] = {
                    "error": str(e),
                    "method": feature_importance_method
                }
            
            # 4. Clustering - mở rộng để bao gồm likert 
            if len(all_numeric_cols) >= 2 and len(df) >= 50:
                try:
                    from sklearn.preprocessing import StandardScaler
                    from sklearn.cluster import KMeans, DBSCAN
                    from sklearn.metrics import silhouette_score
                    import numpy as np

                    clustering_method = self.config.get("ml", {}).get("clustering_method", "kmeans")
                    max_clusters = min(self.config.get("ml", {}).get("max_clusters", 10), len(df) // 20)
                    
                    # Chuẩn hóa dữ liệu
                    X = StandardScaler().fit_transform(df[all_numeric_cols].fillna(0))
                    
                    # Phân tích số lượng cụm tối ưu bằng silhouette score
                    best_n_clusters = 2  # Mặc định
                    best_silhouette_score = -1
                    clustering_details = {}

                    # Thử các số lượng cụm từ 2 đến max_clusters
                    for n_clusters in range(2, min(max_clusters + 1, len(X) // 2)):
                        try:
                            # Sử dụng KMeans
                            if clustering_method == "kmeans":
                                kmeans = KMeans(
                                    n_clusters=n_clusters, 
                                    n_init=10,  # Số lần khởi tạo trung tâm cụm
                                    random_state=42
                                )
                                labels = kmeans.fit_predict(X)
                            
                            # Sử dụng DBSCAN như một phương án thay thế
                            elif clustering_method == "dbscan":
                                dbscan = DBSCAN(
                                    eps=0.5,  # Khoảng cách tối đa giữa hai điểm để được coi là trong cùng một cụm
                                    min_samples=max(2, len(X) // 100)  # Số điểm tối thiểu để tạo thành một cụm
                                )
                                labels = dbscan.fit_predict(X)
                                
                                # Nếu DBSCAN không tạo ra đủ số cụm, bỏ qua
                                if len(np.unique(labels)) < 2:
                                    continue
                            
                            # Tính toán silhouette score
                            if len(np.unique(labels)) > 1:
                                score = silhouette_score(X, labels)
                                
                                # Lưu kết quả nếu tốt hơn
                                if score > best_silhouette_score:
                                    best_silhouette_score = score
                                    best_n_clusters = n_clusters
                                    
                                    # Lưu chi tiết về cụm
                                    if clustering_method == "kmeans":
                                        clustering_details = {
                                            "method": "kmeans",
                                            "n_clusters": n_clusters,
                                            "silhouette_score": float(score),
                                            "cluster_centers": kmeans.cluster_centers_.tolist(),
                                            "cluster_sizes": [
                                                int(np.sum(labels == i)) 
                                                for i in range(n_clusters)
                                            ]
                                        }
                                    elif clustering_method == "dbscan":
                                        clustering_details = {
                                            "method": "dbscan",
                                            "n_clusters": len(np.unique(labels)) - (1 if -1 in labels else 0),
                                            "silhouette_score": float(score),
                                            "cluster_sizes": [
                                                int(np.sum(labels == i)) 
                                                for i in np.unique(labels) if i != -1
                                            ],
                                            "noise_points": int(np.sum(labels == -1))
                                        }
                        
                        except Exception as cluster_err:
                            logger.warning(f"Error in clustering with {n_clusters} clusters: {str(cluster_err)}")
                    
                    # Tạo visualization cho clustering
                    try:
                        # Sử dụng PCA để giảm chiều xuống 2D để visualization
                        from sklearn.decomposition import PCA
                        
                        pca = PCA(n_components=2)
                        X_pca = pca.fit_transform(X)
                        
                        # Tạo nhãn cụm cho dữ liệu gốc
                        if clustering_method == "kmeans":
                            kmeans_final = KMeans(
                                n_clusters=best_n_clusters, 
                                n_init=10, 
                                random_state=42
                            )
                            cluster_labels = kmeans_final.fit_predict(X)
                        elif clustering_method == "dbscan":
                            dbscan_final = DBSCAN(
                                eps=0.5, 
                                min_samples=max(2, len(X) // 100)
                            )
                            cluster_labels = dbscan_final.fit_predict(X)
                        
                        # Tạo dữ liệu cho visualization
                        clustering_viz_data = [
                            {
                                "x": float(X_pca[i, 0]),
                                "y": float(X_pca[i, 1]),
                                "cluster": int(cluster_labels[i])
                            } 
                            for i in range(len(X_pca))
                        ]
                        
                        clustering_details["visualization"] = {
                            "type": "scatter",
                            "data": clustering_viz_data,
                            "x_axis": "PCA Component 1",
                            "y_axis": "PCA Component 2",
                            "title": f"Clustering Visualization ({clustering_method.upper()})"
                        }
                    except Exception as viz_err:
                        logger.warning(f"Error creating clustering visualization: {str(viz_err)}")
                    
                    # Lưu kết quả clustering
                    advanced_results["clustering"] = clustering_details
                    
                except Exception as e:
                    logger.error(f"Error in clustering analysis: {str(e)}")
                    advanced_results["clustering"] = {"error": str(e)}
            
            # 5. Phân tích nâng cao cho Likert scale
            if likert_cols:
                try:
                    # Phân tích cho cột Likert - tìm mẫu trả lời giống nhau
                    likert_analysis = {}
                    
                    if len(likert_cols) >= 2:
                        # Tính ma trận tương quan giữa các cột Likert
                        likert_corr = df[likert_cols].corr(method='spearman').round(2)
                        
                        # Tìm các cặp có tương quan cao
                        high_corr_pairs = []
                        for i, col1 in enumerate(likert_corr.columns):
                            for j, col2 in enumerate(likert_corr.columns):
                                if i < j:  # Chỉ lấy phần tam giác trên
                                    corr_val = likert_corr.loc[col1, col2]
                                    if abs(corr_val) > 0.6:  # Ngưỡng tương quan cao
                                        high_corr_pairs.append({
                                            "question1": col1,
                                            "question2": col2,
                                            "correlation": float(corr_val),
                                            "relationship": "positive" if corr_val > 0 else "negative",
                                            "strength": "strong" if abs(corr_val) > 0.8 else "moderate"
                                        })
                        
                        likert_analysis["correlation"] = {
                            "correlation_matrix": likert_corr.to_dict(),
                            "high_correlation_pairs": high_corr_pairs
                        }
                    
                    # Phát hiện phản hồi không nhất quán
                    inconsistent_responses = {}
                    for col in likert_cols:
                        try:
                            # Tìm phạm vi giá trị
                            scale_min = df[col].min()
                            scale_max = df[col].max()
                            
                            # Tính tỷ lệ phản hồi ở mỗi giá trị
                            value_counts = df[col].value_counts(normalize=True).to_dict()
                            
                            # Phân tích sự phân cực
                            polarization = abs(df[col].skew())
                            
                            inconsistent_responses[col] = {
                                "scale_range": [float(scale_min), float(scale_max)],
                                "distribution": {str(k): float(v) for k, v in value_counts.items()},
                                "polarization": float(polarization),
                                "polarization_type": "high" if polarization > 0.5 else "low"
                            }
                        except Exception as col_err:
                            logger.warning(f"Error analyzing likert column {col}: {str(col_err)}")
                    
                    likert_analysis["response_patterns"] = inconsistent_responses
                    
                    # Phân tích mức độ đồng thuận (Consensus)
                    consensus_analysis = {}
                    for col in likert_cols:
                        # Tính tỷ lệ đồng thuận (tỷ lệ giá trị phổ biến nhất)
                        most_common = df[col].value_counts(normalize=True).max()
                        consensus_level = most_common
                        
                        consensus_analysis[col] = {
                            "consensus_level": float(consensus_level),
                            "interpretation": "high" if consensus_level > 0.7 else "medium" if consensus_level > 0.5 else "low"
                        }
                    
                    likert_analysis["consensus"] = consensus_analysis
                    
                    advanced_results["likert_analysis"] = likert_analysis
                    
                except Exception as e:
                    logger.error(f"Error in Likert scale analysis: {str(e)}")
                    advanced_results["likert_analysis"] = {"error": str(e)}
            
            # 6. Phân tích mẫu trong cột binary
            if binary_cols:
                try:
                    binary_analysis = {}
                    
                    # Phân tích tổng thể
                    if len(binary_cols) >= 2:
                        # Tạo contingency table (bảng liên hợp) cho các cặp cột
                        contingency_tables = {}
                        
                        for i, col1 in enumerate(binary_cols):
                            for j, col2 in enumerate(binary_cols):
                                if i < j:  # Chỉ lấy phần tam giác trên
                                    try:
                                        # Tạo bảng liên hợp
                                        cont_table = pd.crosstab(df[col1], df[col2])
                                        
                                        # Tính Chi-square test để kiểm tra độc lập
                                        chi2, p, dof, expected = stats.chi2_contingency(cont_table)
                                        
                                        contingency_tables[f"{col1}_vs_{col2}"] = {
                                            "table": cont_table.to_dict(),
                                            "chi2": float(chi2),
                                            "p_value": float(p),
                                            "dependent": bool(p < 0.05)
                                        }
                                    except Exception as chi_err:
                                        logger.warning(f"Error computing chi-square for {col1} vs {col2}: {str(chi_err)}")
                        
                        binary_analysis["dependencies"] = contingency_tables
                    
                    # Phân tích từng cột
                    column_analysis = {}
                    for col in binary_cols:
                        value_counts = df[col].value_counts()
                        most_common = value_counts.idxmax()
                        least_common = value_counts.idxmin()
                        
                        column_analysis[col] = {
                            "counts": value_counts.to_dict(),
                            "most_common": {
                                "value": most_common,
                                "count": int(value_counts[most_common]),
                                "percentage": float(value_counts[most_common] / len(df) * 100)
                            },
                            "bias_ratio": float(value_counts.max() / value_counts.min()) if value_counts.min() > 0 else float('inf')
                        }
                    
                    binary_analysis["columns"] = column_analysis
                    
                    advanced_results["binary_patterns"] = binary_analysis
                    
                except Exception as e:
                    logger.error(f"Error in binary pattern analysis: {str(e)}")
                    advanced_results["binary_patterns"] = {"error": str(e)}
            
            # 7. Phân tích cho phân phối giới tính
            if gender_cols:
                try:
                    gender_analysis = {}
                    
                    for col in gender_cols:
                        # Chuẩn hóa giá trị (chuyển về lowercase)
                        gender_values = df[col].astype(str).str.lower()
                        
                        # Tính toán tỷ lệ giới tính
                        value_counts = gender_values.value_counts()
                        
                        # Xác định các giá trị nam/nữ
                        male_terms = {'male', 'm', 'man', 'men', 'boy', 'nam'}
                        female_terms = {'female', 'f', 'woman', 'women', 'girl', 'nữ'}
                        
                        # Tìm các giá trị tương ứng
                        male_values = [v for v in value_counts.index if v in male_terms]
                        female_values = [v for v in value_counts.index if v in female_terms]
                        
                        # Tính tỷ lệ nam/nữ nếu có thể xác định
                        male_count = sum(value_counts.get(v, 0) for v in male_values)
                        female_count = sum(value_counts.get(v, 0) for v in female_values)
                        
                        total_identified = male_count + female_count
                        male_percentage = male_count / total_identified * 100 if total_identified > 0 else 0
                        female_percentage = female_count / total_identified * 100 if total_identified > 0 else 0
                        
                        # Xác định giá trị khác (không phải nam/nữ)
                        other_values = [v for v in value_counts.index if v not in male_terms and v not in female_terms]
                        other_count = sum(value_counts.get(v, 0) for v in other_values)
                        other_percentage = other_count / len(df) * 100
                        
                        gender_analysis[col] = {
                            "distribution": {
                                "male": {
                                    "count": int(male_count),
                                    "percentage": float(male_percentage)
                                },
                                "female": {
                                    "count": int(female_count),
                                    "percentage": float(female_percentage)
                                },
                                "other_or_unknown": {
                                    "count": int(other_count),
                                    "percentage": float(other_percentage),
                                    "values": other_values[:5]  # Chỉ lấy 5 giá trị đầu tiên
                                }
                            },
                            "ratio": float(male_count / female_count) if female_count > 0 else float('inf'),
                            "all_values": value_counts.to_dict()
                        }
                    
                    advanced_results["gender_distribution"] = gender_analysis
                    
                except Exception as e:
                    logger.error(f"Error in gender distribution analysis: {str(e)}")
                    advanced_results["gender_distribution"] = {"error": str(e)}
            
            # 8. Phân tích text nâng cao
            if text_cols and len(df) > 0:
                try:
                    text_analysis = {}
                    
                    for col in text_cols[:3]:  # Giới hạn 3 cột để tránh quá tải
                        # Phân tích độ dài
                        text_lengths = df[col].astype(str).str.len()
                        word_counts = df[col].astype(str).str.split().str.len()
                        
                        # Phân tích từ phổ biến
                        try:
                            from collections import Counter
                            import re
                            
                            # Gộp tất cả text
                            all_text = ' '.join(df[col].astype(str).dropna())
                            
                            # Tách từ và loại bỏ dấu câu
                            words = re.findall(r'\b[a-zA-Z0-9_]+\b', all_text.lower())
                            
                            # Đếm từ
                            word_counts_dict = Counter(words)
                            top_words = dict(word_counts_dict.most_common(20))
                        except Exception as word_err:
                            logger.warning(f"Error in word analysis for column {col}: {str(word_err)}")
                            top_words = {}
                        
                        text_analysis[col] = {
                            "length_statistics": {
                                "mean_length": float(text_lengths.mean()),
                                "std_length": float(text_lengths.std()),
                                "min_length": int(text_lengths.min()),
                                "max_length": int(text_lengths.max()),
                                "mean_words": float(word_counts.mean()),
                                "std_words": float(word_counts.std())
                            },
                            "top_words": top_words
                        }
                    
                    advanced_results["text_analysis"] = text_analysis
                    
                except Exception as e:
                    logger.error(f"Error in text analysis: {str(e)}")
                    advanced_results["text_analysis"] = {"error": str(e)}
            
            # 9. Phân tích cột range
            if range_cols:
                try:
                    range_analysis = {}
                    
                    for col in range_cols:
                        # Tìm các khoảng trong cột
                        range_pattern = r'(\d+)\s*[-–—]\s*(\d+)'
                        ranges = df[col].astype(str).str.extract(range_pattern)
                        
                        if not ranges.empty and not ranges.iloc[:, 0].empty and not ranges.iloc[:, 1].empty:
                            min_vals = pd.to_numeric(ranges.iloc[:, 0], errors='coerce')
                            max_vals = pd.to_numeric(ranges.iloc[:, 1], errors='coerce')
                            
                            # Tính range width
                            range_width = max_vals - min_vals
                            
                            range_analysis[col] = {
                                "range_statistics": {
                                    "mean_min": float(min_vals.mean()),
                                    "mean_max": float(max_vals.mean()),
                                    "mean_width": float(range_width.mean()),
                                    "min_width": float(range_width.min()),
                                    "max_width": float(range_width.max()),
                                    "std_width": float(range_width.std())
                                },
                                "range_examples": df[col].dropna().sample(min(5, df[col].dropna().shape[0])).tolist()
                            }
                        else:
                            range_analysis[col] = {
                                "error": "Could not extract ranges from this column"
                            }
                    
                    advanced_results["range_analysis"] = range_analysis
                    
                except Exception as e:
                    logger.error(f"Error in range analysis: {str(e)}")
                    advanced_results["range_analysis"] = {"error": str(e)}
            
            # Trả về tất cả kết quả phân tích
            return advanced_results
        except Exception as e:
            logger.error(f"Error in advanced analysis: {str(e)}")
            return {"error": str(e)}
            
    def _run_time_series_analysis(self, df: pd.DataFrame) -> Dict:
        # Thay thế phương thức hiện tại:
        
        try:
            time_series_results = {"analyses": [], "datetime_insights": {}, "forecasts": []}
            
            if not hasattr(self, 'column_types') or not self.column_types:
                self.column_types = self.data_processor.get_column_types(df)
            
            # Lấy cột datetime
            datetime_cols = [col for col in self.column_types["datetime"] if col in df.columns]
            
            if not datetime_cols:
                return {"error": "No datetime columns found"}
            
            # Phân tích insights cho mỗi cột datetime 
            for date_col in datetime_cols:
                # Phân tích phân phối thời gian
                try:
                    distribution = analyze_datetime_distribution(df[date_col])
                    time_series_results["datetime_insights"][date_col] = {
                        "range_days": distribution.get("range_days", 0),
                        "distributions": {
                            "year": distribution.get("distributions", {}).get("year", {}),
                            "month": distribution.get("distributions", {}).get("month", {}),
                            "day_of_week": distribution.get("distributions", {}).get("day_of_week", {})
                        },
                        "time_gaps": distribution.get("time_gaps", {}),
                        "suggested_frequency": distribution.get("suggested_frequency", "unknown"),
                        "seasonality": distribution.get("seasonality", {"detected": False})
                    }
                except Exception as e:
                    logger.warning(f"Error analyzing datetime distribution for {date_col}: {str(e)}")
            
            # Tìm các cột numeric
            numeric_cols = [col for col in self.column_types["numeric"] 
                        if col in df.columns 
                        and col not in self.column_types["id"] 
                        and col not in self.column_types["binary"]]
            
            # Giới hạn phân tích
            numeric_cols_to_analyze = numeric_cols[:5]  # Tăng lên 5 cột để phân tích nhiều hơn
            
            for date_col in datetime_cols[:2]:  # Chỉ phân tích 2 cột datetime đầu tiên
                for value_col in numeric_cols_to_analyze:
                    # Kiểm tra đủ dữ liệu
                    valid_data = df[[date_col, value_col]].dropna()
                    if len(valid_data) < 10:
                        continue
                    
                    # Phân tích chuỗi thời gian
                    try:
                        ts_analysis = self.time_series_analyzer.analyze_time_series(
                            df=df, date_col=date_col, value_col=value_col
                        )
                        
                        # Thêm thông tin column và phân phối
                        ts_analysis["date_column"] = date_col
                        ts_analysis["value_column"] = value_col
                        
                        # Dự đoán tần suất dữ liệu nếu không có
                        if "frequency" not in ts_analysis and date_col in time_series_results["datetime_insights"]:
                            ts_analysis["suggested_frequency"] = time_series_results["datetime_insights"][date_col].get("suggested_frequency")
                        
                        # Thêm thông tin về mùa vụ
                        if date_col in time_series_results["datetime_insights"]:
                            ts_analysis["seasonality_info"] = time_series_results["datetime_insights"][date_col].get("seasonality", {})
                        
                        # Thêm vào kết quả
                        time_series_results["analyses"].append(ts_analysis)
                        
                        # Tự động dự báo với default 10 periods
                        try:
                            if self.config.get("ml", {}).get("enable_advanced_forecasting", True):
                                forecast = self.time_series_analyzer.forecast_time_series(
                                    df, date_col, value_col, forecast_periods=10, return_confidence=True
                                )
                                
                                # Add to forecasts
                                if forecast and "forecast" in forecast:
                                    time_series_results["forecasts"].append({
                                        "date_column": date_col,
                                        "value_column": value_col,
                                        "periods": 10,
                                        "forecast_data": forecast
                                    })
                        except Exception as forecast_err:
                            logger.warning(f"Error forecasting time series for {date_col}/{value_col}: {str(forecast_err)}")
                            
                    except Exception as e:
                        logger.error(f"Error analyzing time series for {date_col} / {value_col}: {str(e)}")
            
            # Add seasonality testing using stats
            if len(time_series_results["analyses"]) > 0:
                try:
                    for i, analysis in enumerate(time_series_results["analyses"]):
                        date_col = analysis["date_column"]
                        value_col = analysis["value_column"]
                        
                        # Convert to datetime and sort
                        df_ts = df[[date_col, value_col]].dropna().copy()
                        df_ts[date_col] = pd.to_datetime(df_ts[date_col])
                        df_ts = df_ts.sort_values(by=date_col)
                        
                        # Check if we have enough data points
                        if len(df_ts) >= 24:  # Need at least 2 years of monthly data
                            try:
                                from statsmodels.tsa.seasonal import seasonal_decompose
                                
                                # Resample to regular frequency if needed
                                freq = analysis.get("suggested_frequency", "M")
                                if freq not in ["D", "W", "M", "Q", "Y"]:
                                    freq = "M"  # Default to monthly
                                
                                df_resampled = df_ts.set_index(date_col)[value_col].resample(freq).mean()
                                
                                # Fill missing values after resampling
                                df_resampled = df_resampled.interpolate(method='linear')
                                
                                # Only decompose if we have enough data points after resampling
                                if len(df_resampled) >= 12:
                                    # Get the seasonal period
                                    period = 12 if freq in ["M", "D"] else 4 if freq == "Q" else 52 if freq == "W" else 1
                                    
                                    if period > 1:
                                        # Perform decomposition
                                        decomposition = seasonal_decompose(df_resampled, model='additive', period=period)
                                        
                                        # Add results to the analysis
                                        seasonal_strength = abs(decomposition.seasonal).mean() / (abs(decomposition.trend).mean() + abs(decomposition.seasonal).mean() + abs(decomposition.resid).mean())
                                        
                                        time_series_results["analyses"][i]["seasonal_decomposition"] = {
                                            "frequency": freq,
                                            "period": period,
                                            "seasonal_strength": float(seasonal_strength),
                                            "significant_seasonality": bool(seasonal_strength > 0.3),
                                            "data_points": len(df_resampled)
                                        }
                            except Exception as decompose_err:
                                logger.warning(f"Error in seasonal decomposition: {str(decompose_err)}")
                except Exception as season_err:
                    logger.warning(f"Error in seasonality testing: {str(season_err)}")
            
            # Nếu không phân tích được chuỗi thời gian nào
            if not time_series_results["analyses"]:
                if time_series_results["datetime_insights"]:
                    # Vẫn trả về thông tin về cột datetime nếu có
                    return {
                        "warning": "Could not analyze any time series, but datetime insights are available",
                        "datetime_insights": time_series_results["datetime_insights"]
                    }
                else:
                    return {"error": "Could not analyze any time series"}
            
            return time_series_results
        except Exception as e:
            logger.error(f"Error in time series analysis: {str(e)}")
            return {"error": str(e)}
    
    def _generate_analysis_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Tạo các khuyến nghị phân tích dựa trên đặc điểm dữ liệu"""
        recommendations = []
        try:
            # Sử dụng column_types đã phát hiện từ run_analysis
            if not hasattr(self, 'column_types') or not self.column_types:
                self.column_types = self.data_processor.get_column_types(df)
            
            dt_cols = self.column_types["datetime"]
            if dt_cols:
                recommendations.append(f"Consider time series analysis using the datetime column(s): {', '.join(dt_cols[:3])}")
            
            id_cols = self.column_types["id"]

            numeric_cols = self.column_types["numeric"]
            if len(numeric_cols) >= 2:
                recommendations.append("Analyze correlation between numeric variables to identify important relationships")

            if len(numeric_cols) > 0:
                recommendations.append("Create distribution plots (histograms, box plots) to better understand the data patterns")
            
            categorical_cols = []
            for cat_type in ["categorical", "gender", "email", "phone", "address", "name", "url"]:
                categorical_cols.extend(self.column_types.get(cat_type, []))
                
            if len(categorical_cols) > 0 and len(numeric_cols) > 0:
                recommendations.append("Perform group analysis to compare metrics across different categories")
            
            if len(numeric_cols) >= 3:
                if len(df) >= 100:
                    recommendations.append("Consider predictive modeling with the available numeric features")
            
            if len(numeric_cols) > 10:
                recommendations.append("Apply dimensionality reduction techniques like PCA for better visualization of high-dimensional data")
            
            # Add recommendation for memory optimization if dataset is large
            memory_usage = df.memory_usage(deep=True).sum() / (1024 * 1024)  # MB
            if memory_usage > 100:
                recommendations.append(f"Optimize memory usage (current: {memory_usage:.1f} MB) by using appropriate data types")
            
            # Add recommendation for advanced analytics if enough data
            if len(df) >= 1000 and len(numeric_cols) >= 3:
                recommendations.append("Perform advanced analytics like clustering to identify patterns in the data")
            
            return recommendations
        except Exception as e:
            logger.error(f"Error generating analysis recommendations: {str(e)}")
            return recommendations
    
    def _generate_advanced_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Tạo các khuyến nghị dựa trên phân tích nâng cao"""
        recommendations = []
        
        try:
            # Sử dụng column_types đã phát hiện
            if not hasattr(self, 'column_types') or not self.column_types:
                self.column_types = self.data_processor.get_column_types(df)
            
            # Khuyến nghị dựa trên feature importance
            feature_importance = getattr(self.data_processor, 'feature_importance', {})
            if feature_importance:
                top_features = list(feature_importance.keys())[:3]
                if top_features:
                    recommendations.append(
                        f"Focus on most important features for analysis: {', '.join(top_features)}"
                    )
            
            # Khuyến nghị dựa trên PCA
            if hasattr(self.data_processor, '_pca_models') and 'main' in self.data_processor._pca_models:
                pca_model = self.data_processor._pca_models['main']
                explained_var = np.sum(pca_model.explained_variance_ratio_)
                if explained_var < 0.8:
                    recommendations.append(
                        "Consider feature engineering to better capture data variance (current PCA explains less than 80% of variance)"
                    )
                else:
                    n_components = len(pca_model.explained_variance_ratio_)
                    if n_components < len(pca_model.components_) / 2:
                        recommendations.append(
                            f"Dimensionality reduction with PCA can effectively reduce features from {len(pca_model.components_)} to {n_components} while preserving {explained_var:.1%} of variance"
                        )
            
            # Khuyến nghị về thời gian xử lý
            numeric_cols = self.column_types["numeric"]
            if len(df) > 10000 and len(numeric_cols) > 10:
                recommendations.append(
                    "For faster processing, consider limiting analysis to important features only"
                )
            
            # Khuyến nghị về clustering
            if len(numeric_cols) >= 3 and len(df) >= 200:
                recommendations.append(
                    "Apply clustering to identify natural groupings in your data"
                )
            
            # Khuyến nghị về feature engineering
            datetime_cols = self.column_types["datetime"]
            if datetime_cols and numeric_cols:
                recommendations.append(
                    "Create lag features for time series analysis to capture temporal patterns"
                )
            
            categorical_count = 0
            for cat_type in ["categorical", "gender", "email", "phone", "address", "name", "url"]:
                categorical_count += len(self.column_types.get(cat_type, []))
                
            if categorical_count > 5:
                recommendations.append(
                    "Consider dimensionality reduction for categorical variables using techniques like target encoding"
                )
            
            # Khuyến nghị về data quality
            missing_cols = df.columns[df.isna().any()]
            if len(missing_cols) > 0:
                recommendations.append(
                    "Address missing values before advanced analysis to improve model quality"
                )
            
            # Khuyến nghị về sample size
            if len(df) < 1000 and len(numeric_cols) > 10:
                recommendations.append(
                    "The dataset size might be too small for the number of features. Consider collecting more data or reducing dimensionality."
                )
            
            return recommendations
        except Exception as e:
            logger.error(f"Error generating advanced recommendations: {str(e)}")
            return []

    def recommend_charts(self, df: pd.DataFrame, columns: Optional[List[str]] = None, file_id:Optional[str] = None) -> Dict[str, Dict]:
        """Recommend chart types appropriate to the data"""
        return self.chart_recommender.recommend_charts(df, columns, file_id)

    def get_best_charts(self, df: pd.DataFrame, columns: Optional[List[str]] = None,file_id:Optional[str] = None, top_k: int = 5) -> List[Dict]:
        """Get the top k best charts"""
        return self.chart_recommender.get_best_charts(df, columns, top_k, file_id)
        
    # Phương thức forecast từ TimeSeriesAnalyzer
    
    def forecast_time_series(
        self, 
        df: pd.DataFrame, 
        date_col: str, 
        value_col: str, 
        forecast_periods: int = 10,
        return_confidence: bool = True
    ) -> Dict:
        """
        Dự báo chuỗi thời gian
        
        Args:
            df: DataFrame chứa dữ liệu
            date_col: Tên cột thời gian
            value_col: Tên cột giá trị
            forecast_periods: Số kỳ dự báo
            return_confidence: Có trả về khoảng tin cậy không
            
        Returns:
            Dict: Kết quả dự báo
        """
        return self.time_series_analyzer.forecast_time_series(
            df, date_col, value_col, forecast_periods, return_confidence
        )