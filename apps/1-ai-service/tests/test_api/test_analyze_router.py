from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


def test_get_insights(test_client: TestClient, mock_analyze_service, sample_csv_path):
    """Test endpoint lấy insights từ dữ liệu"""
    request_data = {
        "fileId": "test_file_id",
        "filePath": sample_csv_path
    }
    
    with patch('app.services.validation_service.ValidationService.validate_and_load_file') as mock_validate:
        import pandas as pd
        # Giả lập kết quả của phương thức validate_and_load_file
        mock_validate.return_value = pd.DataFrame({
            'date': pd.date_range(start='2023-01-01', periods=10),
            'value': range(10)
        })
        
        response = test_client.post("/analyze/insights", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "insights" in data["data"]
        
        # Kiểm tra phương thức generate_insights được gọi
        mock_analyze_service.generate_insights.assert_called_once()


def test_get_visualizations(test_client: TestClient, mock_analyze_service, sample_csv_path):
    """Test endpoint tạo biểu đồ trực quan hóa cho dữ liệu"""
    request_data = {
        "fileId": "test_file_id",
        "filePath": sample_csv_path
    }
    
    with patch('app.services.validation_service.ValidationService.validate_and_load_file') as mock_validate:
        import pandas as pd
        mock_validate.return_value = pd.DataFrame({
            'date': pd.date_range(start='2023-01-01', periods=10),
            'value': range(10)
        })
        
        response = test_client.post("/analyze/visualize", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "visualizations" in data["data"]
        
        # Kiểm tra phương thức generate_visualizations được gọi
        mock_analyze_service.generate_visualizations.assert_called_once()


def test_get_predictions(test_client: TestClient, mock_analyze_service, sample_csv_path):
    """Test endpoint tạo dự đoán dựa trên dữ liệu"""
    from app.models.analysis import PredictionResult
    
    # Mock phương thức make_prediction trả về PredictionResult
    mock_analyze_service.make_prediction.return_value = PredictionResult(
        predictions=[{"actual": 1, "predicted": 1.1}],
        metrics={"r2": 0.95, "mae": 0.1},
        modelInfo={"name": "RandomForest"}
    )
    
    request_data = {
        "fileId": "test_file_id",
        "filePath": sample_csv_path,
        "data": {
            "targetColumn": "value",
            "featureColumns": ["date"],
            "modelType": "regression"
        }
    }
    
    with patch('app.services.validation_service.ValidationService.validate_and_load_file') as mock_validate:
        import pandas as pd
        mock_validate.return_value = pd.DataFrame({
            'date': pd.date_range(start='2023-01-01', periods=10),
            'value': range(10)
        })
        
        response = test_client.post("/analyze/predict", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "predictions" in data["data"]
        assert "metrics" in data["data"]
        
        # Kiểm tra phương thức make_prediction được gọi
        mock_analyze_service.make_prediction.assert_called_once()


def test_get_full_analysis(test_client: TestClient, mock_analyze_service, sample_csv_path):
    """Test endpoint phân tích toàn diện dữ liệu"""
    # Mock phương thức run_full_analysis
    mock_analyze_service.run_full_analysis.return_value = {
        "dataset_info": {"rows": 10, "columns": 2},
        "insights": [{"type": "summary", "title": "Dataset Overview"}],
        "visualizations": [{"type": "line", "title": "Sample Chart"}]
    }
    
    request_data = {
        "fileId": "test_file_id",
        "filePath": sample_csv_path
    }
    
    with patch('app.services.validation_service.ValidationService.validate_and_load_file') as mock_validate:
        import pandas as pd
        mock_validate.return_value = pd.DataFrame({
            'date': pd.date_range(start='2023-01-01', periods=10),
            'value': range(10)
        })
        
        response = test_client.post("/analyze/full", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "dataset_info" in data["data"]
        assert "insights" in data["data"]
        
        # Kiểm tra phương thức run_full_analysis được gọi
        mock_analyze_service.run_full_analysis.assert_called_once()


def test_analyze_time_series(test_client: TestClient, sample_csv_path):
    """Test endpoint phân tích chuỗi thời gian"""
    with patch('ml.analysis.forecasting.TimeSeriesAnalyzer') as MockAnalyzer:
        # Mock phương thức analyze_time_series và forecast_time_series
        instance = MockAnalyzer.return_value
        instance.analyze_time_series.return_value = {
            "time_series_info": {"frequency": "D"},
            "statistics": {"mean": 5.0},
            "stationarity": {"is_stationary": True}
        }
        instance.forecast_time_series.return_value = {
            "forecast_data": [{"period": 1, "forecast": 10.5}],
            "metrics": {"mse": 0.1}
        }
        
        request_data = {
            "fileId": "test_file_id",
            "filePath": sample_csv_path,
            "data": {
                "date_column": "date",
                "value_column": "value",
                "forecast": True,
                "forecast_periods": 5
            }
        }
        
        with patch('app.services.validation_service.ValidationService.validate_and_load_file') as mock_validate:
            import pandas as pd
            mock_validate.return_value = pd.DataFrame({
                'date': pd.date_range(start='2023-01-01', periods=10),
                'value': range(10)
            })
            
            response = test_client.post("/analyze/time-series", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert "time_series_info" in data["data"]
            assert "forecast" in data["data"]
            
            # Kiểm tra các phương thức được gọi đúng
            instance.analyze_time_series.assert_called_once()
            instance.forecast_time_series.assert_called_once()


def test_async_full_analysis(test_client: TestClient, sample_csv_path):
    """Test endpoint phân tích bất đồng bộ"""
    with patch('app.core.tasks.BackgroundTaskManager.get_instance') as mock_get_manager:
        # Mock instance của BackgroundTaskManager
        mock_manager = MagicMock()
        mock_manager.submit_task.return_value = {"status": "submitted"}
        mock_get_manager.return_value = mock_manager
        
        request_data = {
            "fileId": "test_file_id",
            "filePath": sample_csv_path
        }
        
        with patch('app.services.validation_service.ValidationService.validate_and_load_file'):
            response = test_client.post("/analyze/async/full", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
            assert data["status"] == "submitted"
            
            # Kiểm tra phương thức submit_task được gọi
            mock_manager.submit_task.assert_called_once()


def test_invalid_request(test_client: TestClient):
    """Test các request không hợp lệ"""
    # Request thiếu fileId và filePath
    request_data = {}
    
    response = test_client.post("/analyze/insights", json=request_data)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    
    # Request tới endpoint predict thiếu data
    request_data = {
        "fileId": "test_file_id",
        "filePath": "test_path.csv"
    }
    
    response = test_client.post("/analyze/predict", json=request_data)
    assert response.status_code == 400