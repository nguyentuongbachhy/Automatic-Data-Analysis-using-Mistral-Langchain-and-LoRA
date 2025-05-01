import pytest
import os
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.models.chat import ChatMessage, MessageRole, UserIntent, IntentType
from app.models.common import MLServiceRequest, SuccessResponse
from app.services.chat_service import ChatService
from app.services.model_service import ModelService


class TestChatServiceIntegration:
    """Integration tests cho ChatService"""

    @pytest.fixture(autouse=True)
    def setup(self, sample_csv_path):
        """Set up riêng cho mỗi test"""
        # Instance của ChatService
        self.chat_service = ChatService()
        
        # Tạo test request
        self.test_request = MLServiceRequest(
            query="Analyze this data",
            fileId="test_file_id",
            filePath=sample_csv_path,
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"}
            ]
        )
        
        # Sample DataFrame
        self.sample_df = pd.DataFrame({
            'numeric_col': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'category_col': ['A', 'B', 'A', 'C', 'B', 'A', 'C', 'B', 'A', 'B'],
            'date_col': pd.date_range(start='2023-01-01', periods=10),
            'value_col': [10, 25, 30, 15, 20, 35, 40, 45, 50, 55]
        })

    @pytest.mark.asyncio
    @patch('app.api.routers.chat_router.ChatService.generate_response')
    async def test_process_message_endpoint(self, mock_generate_response):
        """Test endpoint /chat/message"""
        # Setup mock
        mock_response = {
            "response": "This is a test response",
            "visualizations": [{"type": "bar", "title": "Test Chart"}],
            "insights": None,
            "commands": None
        }
        mock_generate_response.return_value = mock_response
        
        # Test the endpoint
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/chat/message", json=self.test_request.dict())
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["response"] == "This is a test response"
        assert len(data["data"]["visualizations"]) == 1

    @pytest.mark.asyncio
    @patch('app.api.routers.chat_router.ChatService.stream_response')
    async def test_stream_message_endpoint(self, mock_stream_response):
        """Test endpoint /chat/stream"""
        # Setup mock
        async def mock_stream():
            yield "This "
            yield "is "
            yield "a "
            yield "stream "
            yield "response"
            yield {"message_id": "test_id", "visualizations": [{"type": "bar"}]}
            
        mock_stream_response.return_value = mock_stream()
        
        # Test the endpoint (không dễ để test SSE endpoint trong unit test)
        # Nhưng chúng ta có thể test format_sse_event function
        from app.api.routers.chat_router import format_sse_event
        
        text_event = format_sse_event("message", {"content": "test content"})
        assert text_event["event"] == "message"
        
        data_event = format_sse_event("data", {"chart": "test chart"})
        assert data_event["event"] == "data"

    @pytest.mark.asyncio
    @patch('app.services.model_service.ModelService.detect_intent')
    @patch('app.services.model_service.ModelService.generate_text')
    async def test_generate_response_with_real_data(self, mock_generate_text, mock_detect_intent):
        """Test tích hợp của hàm generate_response với dữ liệu thực tế"""
        # Setup mocks
        mock_detect_intent.return_value = UserIntent(
            intent=IntentType.QUESTION,
            confidence=0.9,
            entities={},
            parameters={}
        )
        mock_generate_text.return_value = "The average of numeric_col is 5.5 and there are 3 categories in category_col."
        
        # Gọi method
        messages = [ChatMessage(role="user", content="What's in this data?")]
        response = await self.chat_service.generate_response(
            "Tell me about this data", messages, self.sample_df, "test_file_id"
        )
        
        # Verify
        assert response.response == "The average of numeric_col is 5.5 and there are 3 categories in category_col."
        assert response.visualizations is None

    @pytest.mark.asyncio
    @patch('app.services.model_service.ModelService.detect_intent')
    @patch('app.services.model_service.ModelService.generate_text')
    async def test_generate_response_with_visualization_intent(self, mock_generate_text, mock_detect_intent, sample_csv_path):
        """Test tích hợp với intent visualization"""
        # Setup mocks
        mock_detect_intent.return_value = UserIntent(
            intent=IntentType.VISUALIZATION,
            confidence=0.9,
            entities={},
            parameters={},
            visualization_type="bar",
            columns=["category_col", "value_col"]
        )
        mock_generate_text.return_value = "Here's a bar chart of value_col by category_col."
        
        # Patch os.path.join để tránh phụ thuộc vào hệ thống file
        with patch('os.path.join', return_value=sample_csv_path):
            # Gọi method
            messages = [ChatMessage(role="user", content="Show me a bar chart")]
            response = await self.chat_service.generate_response(
                "Create a bar chart of value by category", messages, self.sample_df, "test_file_id"
            )
        
        # Verify
        assert response.response == "Here's a bar chart of value_col by category_col."
        assert response.visualizations is not None
        assert len(response.visualizations) > 0
        assert response.visualizations[0]["type"] == "bar"

    @pytest.mark.asyncio
    @patch('app.services.model_service.ModelService.detect_intent')
    @patch('app.services.model_service.ModelService.generate_text_stream')
    async def test_stream_response_with_real_data(self, mock_generate_text_stream, mock_detect_intent):
        """Test tích hợp của hàm stream_response với dữ liệu thực tế"""
        # Setup mocks
        mock_detect_intent.return_value = UserIntent(
            intent=IntentType.QUESTION,
            confidence=0.9,
            entities={},
            parameters={}
        )
        
        async def mock_stream():
            yield "The "
            yield "average "
            yield "is "
            yield "5.5."
            
        mock_generate_text_stream.return_value = mock_stream()
        
        # Gọi method
        messages = [ChatMessage(role="user", content="What's the average?")]
        
        # Collect all stream chunks
        chunks = []
        async for chunk in self.chat_service.stream_response(
            "What is the average of numeric_col?", messages, self.sample_df, "test_file_id", "test_message_id"
        ):
            chunks.append(chunk)
        
        # Verify
        assert len(chunks) == 4
        assert chunks[0] == "The "
        assert chunks[3] == "5.5."

    @pytest.mark.asyncio
    @patch('app.services.model_service.ModelService.detect_intent')
    async def test_create_chart_integration(self, mock_detect_intent):
        """Test tích hợp của các hàm tạo chart với dữ liệu thực tế"""
        # Setup mock
        mock_detect_intent.return_value = UserIntent(
            intent=IntentType.VISUALIZATION,
            confidence=0.9,
            entities={},
            parameters={},
            visualization_type="bar",
            columns=["category_col"]
        )
        
        # Bar chart
        bar_chart = self.chat_service._create_bar_chart(
            self.sample_df, ["category_col"], "Bar Chart Test", {}
        )
        
        assert bar_chart.type == "bar"
        assert len(bar_chart.data) == 3  # 3 categories: A, B, C
        
        # Pie chart
        pie_chart = self.chat_service._create_pie_chart(
            self.sample_df, ["category_col"], "Pie Chart Test", {}
        )
        
        assert pie_chart.type == "pie"
        assert len(pie_chart.data) == 3
        
        # Line chart with date
        line_chart = self.chat_service._create_line_chart(
            self.sample_df, ["date_col", "value_col"], "Line Chart Test", {}
        )
        
        assert line_chart.type == "line"
        assert len(line_chart.data) == 10
        
        # Scatter chart
        scatter_chart = self.chat_service._create_scatter_chart(
            self.sample_df, ["numeric_col", "value_col"], "Scatter Chart Test", {}
        )
        
        assert scatter_chart.type == "scatter"
        assert len(scatter_chart.data) == 10
        
        # Histogram
        histogram = self.chat_service._create_histogram_chart(
            self.sample_df, ["value_col"], "Histogram Test", {"bins": 5}
        )
        
        assert histogram.type == "bar"  # Histogram hiển thị dạng bar
        assert len(histogram.data) == 5  # 5 bins