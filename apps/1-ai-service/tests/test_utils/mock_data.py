import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import tempfile
import os
from datetime import datetime, timedelta

from app.models.analysis import InsightData, InsightType, VisualizationData, ChartType
from app.models.chat import ChatMessage


def create_sample_dataframe(rows: int = 100, include_date: bool = True, include_categorical: bool = True) -> pd.DataFrame:
    """Tạo DataFrame mẫu cho tests"""
    data = {
        'numeric1': np.random.randn(rows).cumsum(),  # Dạng chuỗi thời gian
        'numeric2': np.random.rand(rows) * 100,      # Giá trị ngẫu nhiên từ 0-100
    }
    
    if include_date:
        start_date = datetime(2023, 1, 1)
        data['date'] = [start_date + timedelta(days=i) for i in range(rows)]
    
    if include_categorical:
        data['category'] = np.random.choice(['A', 'B', 'C', 'D'], rows)
        
    # Thêm một số giá trị null
    data['numeric_with_nulls'] = np.random.randn(rows)
    null_indices = np.random.choice(rows, size=rows//10, replace=False)
    data['numeric_with_nulls'][null_indices] = np.nan
    
    return pd.DataFrame(data)


def create_sample_csv_file(df: Optional[pd.DataFrame] = None) -> str:
    """Tạo file CSV tạm thời từ DataFrame"""
    if df is None:
        df = create_sample_dataframe()
    
    # Tạo file tạm
    fd, path = tempfile.mkstemp(suffix='.csv')
    df.to_csv(path, index=False)
    os.close(fd)
    
    return path


def get_sample_chat_messages() -> List[ChatMessage]:
    """Tạo các tin nhắn chat mẫu"""
    return [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi there! How can I help you?"),
        ChatMessage(role="user", content="Can you analyze my data?")
    ]


def get_sample_insights() -> List[InsightData]:
    """Tạo insights mẫu"""
    return [
        InsightData(
            type=InsightType.SUMMARY, 
            title="Dataset Overview",
            content="Dataset contains 100 rows and 4 columns with no missing values.",
            importance=10
        ),
        InsightData(
            type=InsightType.CORRELATION,
            title="Strong Correlation",
            content="There is a strong positive correlation (0.85) between numeric1 and numeric2.",
            importance=8,
            columns=["numeric1", "numeric2"]
        ),
        InsightData(
            type=InsightType.TREND,
            title="Increasing Trend",
            content="numeric1 shows an increasing trend over time, rising by 45.2% from the earliest to the latest period.",
            importance=7,
            columns=["date", "numeric1"]
        )
    ]


def get_sample_visualizations() -> List[VisualizationData]:
    """Tạo visualizations mẫu"""
    return [
        VisualizationData(
            type=ChartType.LINE,
            title="numeric1 over Time",
            description="Line chart showing changes in numeric1 over time",
            data=[{"time": f"2023-01-{i+1:02d}", "value": float(i)} for i in range(30)],
            config={
                "xAxis": {"key": "time", "name": "Date"},
                "yAxis": {"key": "value", "name": "Value"},
                "width": 800,
                "height": 400
            }
        ),
        VisualizationData(
            type=ChartType.BAR,
            title="Distribution by Category",
            description="Bar chart showing the distribution of values by category",
            data=[
                {"category": "A", "value": 30},
                {"category": "B", "value": 25},
                {"category": "C", "value": 20},
                {"category": "D", "value": 25}
            ],
            config={
                "xAxis": {"key": "category", "name": "Category"},
                "yAxis": {"key": "value", "name": "Count"},
                "width": 600,
                "height": 400
            }
        ),
        VisualizationData(
            type=ChartType.SCATTER,
            title="numeric1 vs numeric2",
            description="Scatter plot showing the relationship between numeric1 and numeric2",
            data=[{"x": float(i), "y": float(i*1.5 + np.random.randn()*5)} for i in range(20)],
            config={
                "xAxis": {"key": "x", "name": "numeric1"},
                "yAxis": {"key": "y", "name": "numeric2"},
                "width": 600,
                "height": 400
            }
        )
    ]


def create_mock_response(model_output: str) -> Dict:
    """Tạo response giả lập từ mô hình"""
    return {
        "success": True,
        "data": {
            "response": model_output
        }
    }


def create_mock_prediction_result() -> Dict:
    """Tạo kết quả dự đoán giả lập"""
    return {
        "predictions": [
            {"actual": 10.5, "predicted": 11.2, "error": 0.7},
            {"actual": 15.3, "predicted": 14.8, "error": -0.5},
            {"actual": 8.7, "predicted": 9.3, "error": 0.6}
        ],
        "metrics": {
            "r2": 0.92,
            "mae": 0.6,
            "rmse": 0.72
        },
        "modelInfo": {
            "name": "RandomForestRegressor",
            "parameters": {"n_estimators": 100, "max_depth": 10}
        }
    }


def create_mock_time_series_analysis() -> Dict:
    """Tạo kết quả phân tích chuỗi thời gian giả lập"""
    return {
        "time_series_info": {
            "original_length": 100,
            "resampled_length": 100,
            "frequency": "D",
            "start_date": "2023-01-01T00:00:00",
            "end_date": "2023-04-10T00:00:00",
            "date_range_days": 100
        },
        "statistics": {
            "mean": 45.23,
            "std": 15.67,
            "min": 10.5,
            "max": 95.8,
            "median": 42.7
        },
        "stationarity": {
            "is_stationary": False,
            "adf_test": {
                "adf_statistic": -2.1,
                "p_value": 0.28,
                "critical_values": {"1%": -3.5, "5%": -2.9, "10%": -2.6}
            }
        },
        "decomposition": {
            "has_seasonality": True,
            "seasonality_strength": 0.45
        },
        "forecast": {
            "forecast_data": [
                {"period": 1, "date": "2023-04-11T00:00:00", "forecast": 96.7},
                {"period": 2, "date": "2023-04-12T00:00:00", "forecast": 97.3},
                {"period": 3, "date": "2023-04-13T00:00:00", "forecast": 98.2}
            ],
            "metrics": {
                "mse": 5.23,
                "mae": 1.89
            }
        }
    }