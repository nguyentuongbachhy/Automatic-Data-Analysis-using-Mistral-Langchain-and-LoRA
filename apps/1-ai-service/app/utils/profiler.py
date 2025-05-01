import time
import logging
import inspect
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast
import functools
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Type variable for decorator
F = TypeVar('F', bound=Callable[..., Any])

def profile_time(func: F) -> F:
    """Decorator để đo thời gian thực thi hàm"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        
        # Lấy tên class nếu là method
        if len(args) > 0 and hasattr(args[0], "__class__"):
            class_name = args[0].__class__.__name__
            logger.info(f"{class_name}.{func.__name__} executed in {duration:.4f}s")
        else:
            logger.info(f"{func.__name__} executed in {duration:.4f}s")
            
        return result
    
    return cast(F, wrapper)

def memory_profile(func: F) -> F:
    """Decorator để đo mức sử dụng bộ nhớ"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / (1024 * 1024)  # MB
        
        result = func(*args, **kwargs)
        
        mem_after = process.memory_info().rss / (1024 * 1024)  # MB
        mem_diff = mem_after - mem_before
        
        # Lấy tên class nếu là method
        if len(args) > 0 and hasattr(args[0], "__class__"):
            class_name = args[0].__class__.__name__
            logger.info(f"{class_name}.{func.__name__} memory usage: {mem_diff:.2f} MB")
        else:
            logger.info(f"{func.__name__} memory usage: {mem_diff:.2f} MB")
            
        return result
    
    return cast(F, wrapper)

class DataProfiler:
    """Profiler để phân tích dataset"""
    
    @classmethod
    def profile_dataframe(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Tạo profile đầy đủ cho DataFrame"""
        if df is None or df.empty:
            return {"error": "DataFrame is empty or None"}
            
        try:
            start_time = time.time()
            
            # Thông tin cơ bản
            basic_info = {
                "rows": len(df),
                "columns": len(df.columns),
                "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
                "duplicate_rows": df.duplicated().sum()
            }
            
            # Thông tin cột
            column_info = {}
            for col in df.columns:
                column_info[col] = cls._profile_column(df, col)
                
            # Phân tích tương quan cho các cột numeric
            correlation = None
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) >= 2:
                corr_matrix = df[numeric_cols].corr()
                
                # Tạo danh sách các cặp tương quan
                correlations = []
                for i in range(len(numeric_cols)):
                    for j in range(i + 1, len(numeric_cols)):
                        col1 = numeric_cols[i]
                        col2 = numeric_cols[j]
                        corr_val = corr_matrix.loc[col1, col2]
                        if not pd.isna(corr_val):
                            correlations.append({
                                "column1": col1,
                                "column2": col2,
                                "correlation": corr_val
                            })
                
                # Sắp xếp theo độ lớn của tương quan
                correlations = sorted(correlations, key=lambda x: abs(x["correlation"]), reverse=True)
                correlation = {
                    "matrix": corr_matrix.to_dict(),
                    "strongest_pairs": correlations[:10]  # Top 10 cặp tương quan mạnh nhất
                }
            
            # Thống kê missing values
            missing_stats = {
                "total_missing": df.isna().sum().sum(),
                "missing_percent": (df.isna().sum().sum() / (df.shape[0] * df.shape[1])) * 100,
                "columns_with_missing": df.isna().sum()[df.isna().sum() > 0].to_dict()
            }
            
            # Tổng hợp kết quả
            profile = {
                "basic_info": basic_info,
                "column_info": column_info,
                "missing_stats": missing_stats,
                "correlation": correlation,
                "execution_time": time.time() - start_time
            }
            
            return profile
        except Exception as e:
            logger.error(f"Error profiling DataFrame: {str(e)}", exc_info=e)
            return {"error": str(e)}
    
    @classmethod
    def _profile_column(cls, df: pd.DataFrame, column: str) -> Dict[str, Any]:
        """Tạo profile cho một cột"""
        try:
            col_data = df[column]
            non_null_count = col_data.count()
            
            # Thông tin cơ bản
            profile = {
                "dtype": str(col_data.dtype),
                "count": len(col_data),
                "non_null_count": non_null_count,
                "null_count": len(col_data) - non_null_count,
                "null_percent": ((len(col_data) - non_null_count) / len(col_data)) * 100 if len(col_data) > 0 else 0,
                "unique_count": col_data.nunique()
            }
            
            # Thêm thống kê phù hợp với kiểu dữ liệu
            if pd.api.types.is_numeric_dtype(col_data):
                # Thống kê cho dữ liệu số
                numeric_stats = col_data.describe().to_dict()
                profile.update(numeric_stats)
                
                # Thêm thông tin phân phối
                non_null = col_data.dropna()
                if len(non_null) > 0:
                    profile["skewness"] = float(non_null.skew())
                    profile["kurtosis"] = float(non_null.kurt())
                    
                    # Phát hiện outlier bằng IQR
                    q1 = float(non_null.quantile(0.25))
                    q3 = float(non_null.quantile(0.75))
                    iqr = q3 - q1
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    
                    outliers = non_null[(non_null < lower_bound) | (non_null > upper_bound)]
                    profile["outlier_count"] = len(outliers)
                    profile["outlier_percent"] = (len(outliers) / len(non_null)) * 100 if len(non_null) > 0 else 0
            
            elif pd.api.types.is_string_dtype(col_data) or pd.api.types.is_categorical_dtype(col_data):
                # Thống kê cho dữ liệu chuỗi/categorical
                non_null = col_data.dropna()
                
                # Tính độ dài trung bình
                if non_null.count() > 0:
                    profile["avg_length"] = non_null.astype(str).str.len().mean()
                
                # Lấy top giá trị
                value_counts = non_null.value_counts()
                if len(value_counts) > 0:
                    top_values = value_counts.head(10).to_dict()
                    profile["top_values"] = top_values
                    
                    top_percent = (value_counts.iloc[0] / non_null.count()) * 100 if non_null.count() > 0 else 0
                    profile["top_value_percent"] = top_percent
            
            elif pd.api.types.is_datetime64_any_dtype(col_data):
                # Thống kê cho dữ liệu datetime
                non_null = col_data.dropna()
                if len(non_null) > 0:
                    profile["min"] = non_null.min().isoformat()
                    profile["max"] = non_null.max().isoformat()
                    profile["range_days"] = (non_null.max() - non_null.min()).total_seconds() / (60 * 60 * 24)
                    
                    # Phân tích timeframe
                    if len(non_null) >= 2:
                        sorted_dates = non_null.sort_values()
                        time_diffs = sorted_dates.diff().dropna()
                        
                        if len(time_diffs) > 0:
                            profile["avg_time_diff_days"] = time_diffs.mean().total_seconds() / (60 * 60 * 24)
                            profile["min_time_diff_days"] = time_diffs.min().total_seconds() / (60 * 60 * 24)
                            profile["max_time_diff_days"] = time_diffs.max().total_seconds() / (60 * 60 * 24)
                
            return profile
        except Exception as e:
            logger.error(f"Error profiling column {column}: {str(e)}")
            return {"error": str(e)}