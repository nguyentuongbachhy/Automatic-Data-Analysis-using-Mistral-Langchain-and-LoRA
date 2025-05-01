from fastapi.testclient import TestClient


def test_health_check(test_client: TestClient):
    """Test endpoint kiểm tra sức khỏe cơ bản"""
    response = test_client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ai-service"


def test_service_status(test_client: TestClient, mock_model_service):
    """Test endpoint kiểm tra trạng thái chi tiết của service"""
    response = test_client.get("/health/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "model" in data
    assert "system" in data


def test_clear_cache(test_client: TestClient, mock_model_service):
    """Test endpoint xóa cache"""
    response = test_client.post("/health/clear-cache")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "message" in data
    assert "Cache cleared successfully" in data["message"]
    # Kiểm tra xem phương thức clear_cache có được gọi không
    mock_model_service.clear_cache.assert_called_once()