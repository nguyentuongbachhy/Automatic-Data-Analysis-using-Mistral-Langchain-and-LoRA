from fastapi.testclient import TestClient
from unittest.mock import patch


def test_process_message_without_file(test_client: TestClient, mock_model_service):
    """Test xử lý tin nhắn chat không có file đính kèm"""
    request_data = {
        "query": "Phân tích dữ liệu này cho tôi",
        "messages": [
            {"role": "user", "content": "Xin chào"},
            {"role": "assistant", "content": "Tôi có thể giúp gì cho bạn?"}
        ]
    }
    
    response = test_client.post("/chat/message", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "response" in data["data"]
    
    # Kiểm tra nội dung response
    assert data["data"]["response"] == "Đây là phản hồi mẫu từ model"
    
    # Kiểm tra xem phương thức generate_text của model service có được gọi không
    mock_model_service.generate_text.assert_called_once()


def test_process_message_with_file(test_client: TestClient, mock_model_service, sample_csv_path):
    """Test xử lý tin nhắn chat có file đính kèm"""
    request_data = {
        "query": "Phân tích dữ liệu này cho tôi",
        "fileId": "test_file_id",
        "filePath": sample_csv_path,
        "messages": []
    }
    
    with patch('app.services.validation_service.ValidationService.validate_and_load_file') as mock_validate:
        import pandas as pd
        # Giả lập kết quả của phương thức validate_and_load_file
        mock_validate.return_value = pd.DataFrame({
            'date': pd.date_range(start='2023-01-01', periods=10),
            'value': range(10)
        })
        
        response = test_client.post("/chat/message", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        
        # Kiểm tra phương thức validate_and_load_file được gọi với đúng tham số
        mock_validate.assert_called_once_with(sample_csv_path)


def test_stream_message(test_client: TestClient, mock_model_service_async):
    """Test stream tin nhắn chat"""
    request_data = {
        "query": "Phân tích dữ liệu này cho tôi",
        "messages": []
    }
    
    response = test_client.post("/chat/stream", json=request_data)
    assert response.status_code == 200
    
    # Kiểm tra định dạng của server-sent events (SSE)
    content = response.content.decode('utf-8')
    assert 'event: message' in content
    assert 'data: ' in content


def test_process_message_invalid_request(test_client: TestClient):
    """Test xử lý tin nhắn với request không hợp lệ"""
    # Request thiếu trường query
    request_data = {
        "messages": []
    }
    
    response = test_client.post("/chat/message", json=request_data)
    assert response.status_code == 400
    
    # Kiểm tra thông báo lỗi
    data = response.json()
    assert "detail" in data
    assert "query is required" in data["detail"]


def test_stream_message_invalid_request(test_client: TestClient):
    """Test stream tin nhắn với request không hợp lệ"""
    # Request thiếu trường query
    request_data = {
        "messages": []
    }
    
    response = test_client.post("/chat/stream", json=request_data)
    assert response.status_code == 200  # SSE vẫn trả về 200 ngay cả khi có lỗi
    
    # Kiểm tra nội dung lỗi trong SSE
    content = response.content.decode('utf-8')
    assert 'event: error' in content