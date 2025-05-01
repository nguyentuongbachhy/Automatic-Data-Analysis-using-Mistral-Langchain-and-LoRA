import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
import os
from datetime import datetime

# Import các module cần thiết
from app.services.chat_service import ChatService
from app.models.chat import ChatMessage, ChatResponse, IntentType, UserIntent
from app.models.analysis import ChartType, VisualizationData


class TestChatService:
    """Test cases cho ChatService"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up cho các test cases"""
        # Tạo mock cho ModelService để không cần thiết model thật
        self.model_service_mock = MagicMock()
        
        # Tạo mock cho config
        self.config_mock = {
            "prompt_template": {
                "system_prompt": "You are DataSenseAI, a helpful assistant."
            }
        }
        
        # Patch ModelService.get_instance để trả về mock
        with patch('app.services.chat_service.ModelService') as self.model_service_cls:
            self.model_service_cls.get_instance.return_value = self.model_service_mock
            
            # Patch ModelConfig để trả về config mock
            with patch('app.services.chat_service.ModelConfig') as self.config_cls:
                self.config_mock_instance = MagicMock()
                self.config_mock_instance.config = self.config_mock
                self.config_cls.return_value = self.config_mock_instance
                
                # Tạo instance của ChatService để test
                self.chat_service = ChatService()
                
                # Sample data để test
                self.sample_df = pd.DataFrame({
                    'numeric_col': [1, 2, 3, 4, 5],
                    'category_col': ['A', 'B', 'A', 'C', 'B'],
                    'datetime_col': pd.date_range(start='2023-01-01', periods=5)
                })
                
                self.sample_messages = [
                    ChatMessage(role="user", content="Hello"),
                    ChatMessage(role="assistant", content="Hi there")
                ]
                
                yield
    
    def test_init(self):
        """Test khởi tạo ChatService"""
        assert self.chat_service is not None
        assert self.chat_service.system_prompt == "You are DataSenseAI, a helpful assistant."
        
    def test_prepare_prompt(self):
        """Test hàm _prepare_prompt"""
        # Test với dataframe
        query = "Analyze this data"
        prompt = self.chat_service._prepare_prompt(query, [], self.sample_df, "test_file_id")
        
        # Kiểm tra các thành phần quan trọng trong prompt
        assert "<system>" in prompt
        assert "You are DataSenseAI" in prompt
        assert "<file>" in prompt
        assert "File ID: test_file_id" in prompt
        assert "Rows: 5" in prompt
        assert "Columns: numeric_col, category_col, datetime_col" in prompt
        assert "<user>" in prompt
        assert query in prompt
        assert "<assistant>" in prompt
        
        # Test với message history
        prompt_with_history = self.chat_service._prepare_prompt(
            query, self.sample_messages, self.sample_df, "test_file_id"
        )
        assert "<user>\nHello\n</user>" in prompt_with_history
        assert "<assistant>\nHi there\n</assistant>" in prompt_with_history
        
        # Test không có dataframe
        prompt_no_df = self.chat_service._prepare_prompt(query, [], None, None)
        assert "<file>" not in prompt_no_df
    
    @pytest.mark.asyncio
    @patch('app.services.chat_service.AnalyzeService')
    async def test_generate_response(self, analyze_service_mock):
        """Test hàm generate_response"""
        # Set up mocks
        intent_mock = UserIntent(intent=IntentType.QUESTION, confidence=0.9, entities={}, parameters={})
        self.model_service_mock.detect_intent.return_value = intent_mock
        self.model_service_mock.generate_text.return_value = "This is a test response"
        
        # Test basic response without dataframe
        response = await self.chat_service.generate_response(
            "Test query", [], None, None
        )
        
        # Verify response
        assert isinstance(response, ChatResponse)
        assert response.response == "This is a test response"
        assert response.visualizations is None
        assert response.insights is None
        
        # Test với dataframe và intent VISUALIZATION
        # Setup mocks
        intent_viz_mock = UserIntent(
            intent=IntentType.VISUALIZATION, 
            confidence=0.9, 
            entities={}, 
            parameters={},
            visualization_type="bar",
            columns=["numeric_col"]
        )
        self.model_service_mock.detect_intent.return_value = intent_viz_mock
        
        # Mock AnalyzeService
        analyze_instance = analyze_service_mock.return_value
        visualization_data = VisualizationData(
            type=ChartType.BAR,
            title="Test Chart",
            data=[{"x": 1, "y": 2}],
            config={}
        )
        
        # Sửa để sử dụng model_dump thay vì dict
        # Mock AnalyzeService.generate_visualizations để trả về list
        visualization_mock = MagicMock()
        visualization_mock.type = ChartType.BAR
        visualization_mock.title = "Test Chart"
        visualization_mock.data = [{"x": 1, "y": 2}]
        visualization_mock.config = {}
        visualization_mock.model_dump.return_value = {
            "type": "bar",
            "title": "Test Chart",
            "data": [{"x": 1, "y": 2}],
            "config": {}
        }
        
        analyze_instance.generate_visualizations.return_value = [visualization_mock]
        
        # Mock os.path.join để tránh phụ thuộc vào hệ thống file
        with patch('os.path.join', return_value="mocked_path"):
            response = await self.chat_service.generate_response(
                "Create a bar chart", [], self.sample_df, "test_file_id"
            )
        
        # Verify
        assert response.response == "This is a test response"
        assert response.visualizations is not None
        assert len(response.visualizations) == 1
        assert response.visualizations[0]["type"] == "bar"
    
    @pytest.mark.asyncio
    @patch('app.services.chat_service.AnalyzeService')
    async def test_stream_response(self, analyze_service_mock):
        """Test hàm stream_response"""
        # Set up mocks
        intent_mock = UserIntent(intent=IntentType.QUESTION, confidence=0.9, entities={}, parameters={})
        self.model_service_mock.detect_intent.return_value = intent_mock
        
        # Important: Mock cho stream_response phải trả về một async generator
        async def mock_generator():
            yield "This "
            yield "is "
            yield "a "
            yield "test "
            yield "response"
        
        self.model_service_mock.generate_text_stream.return_value = mock_generator()
        
        # Test stream response
        message_id = "test_message_id"
        chunks = []
        async for chunk in self.chat_service.stream_response(
            "Test query", [], None, None, message_id
        ):
            chunks.append(chunk)
        
        # Verify
        assert len(chunks) == 5
        assert chunks[0] == "This "
        assert chunks[1] == "is "
        
        # Test stream with visualization intent
        intent_viz_mock = UserIntent(
            intent=IntentType.VISUALIZATION, 
            confidence=0.9, 
            entities={}, 
            parameters={},
            visualization_type="bar",
            columns=["numeric_col"]
        )
        self.model_service_mock.detect_intent.return_value = intent_viz_mock
        
        # Reset mock
        async def mock_viz_generator():
            yield "This "
            yield "is "
            yield "a "
            yield "chart "
            yield "response"
        
        self.model_service_mock.generate_text_stream.return_value = mock_viz_generator()
        
        # Mock AnalyzeService
        analyze_instance = analyze_service_mock.return_value
        
        # Sửa để sử dụng model_dump thay vì dict
        visualization_mock = MagicMock()
        visualization_mock.type = ChartType.BAR
        visualization_mock.title = "Test Chart"
        visualization_mock.data = [{"x": 1, "y": 2}]
        visualization_mock.config = {}
        visualization_mock.model_dump.return_value = {
            "type": "bar",
            "title": "Test Chart",
            "data": [{"x": 1, "y": 2}],
            "config": {}
        }
        
        analyze_instance.generate_visualizations.return_value = [visualization_mock]
        
        # Test with dataframe
        with patch('os.path.join', return_value="mocked_path"):
            chunks = []
            async for chunk in self.chat_service.stream_response(
                "Create a chart", [], self.sample_df, "test_file_id", message_id
            ):
                chunks.append(chunk)
            
            # Verify chunks
            assert "\n\nGenerating visualizations...\n" in chunks
            
            # Verify visualization data
            viz_chunk = None
            for chunk in chunks:
                if isinstance(chunk, dict) and "visualizations" in chunk:
                    viz_chunk = chunk
                    break
            
            assert viz_chunk is not None
            assert viz_chunk["message_id"] == message_id
            assert len(viz_chunk["visualizations"]) == 1
    
    @pytest.mark.asyncio
    @patch('app.services.chat_service.AnalyzeService')
    async def test_generate_visualizations_from_intent(self, analyze_service_mock):
        """Test hàm _generate_visualizations_from_intent"""
        # Set up mocks
        intent_viz = UserIntent(
            intent=IntentType.VISUALIZATION, 
            confidence=0.9, 
            entities={}, 
            parameters={},
            visualization_type="bar",
            columns=["numeric_col"]
        )
        
        # Mock AnalyzeService
        analyze_instance = analyze_service_mock.return_value
        
        # Create a proper mock for VisualizationData
        viz_mock = MagicMock(spec=VisualizationData)
        viz_mock.type = ChartType.BAR
        viz_mock.title = "Test Chart"
        viz_mock.data = [{"x": 1, "y": 2}]
        viz_mock.config = {}
        
        analyze_instance.generate_visualizations.return_value = [viz_mock]
        
        # Test visualization intent
        result = await self.chat_service._generate_visualizations_from_intent(
            intent_viz, self.sample_df, "test_file_id", analyze_instance
        )
        
        assert len(result) == 1
        assert result[0].type == ChartType.BAR
        
        # Test without columns in intent
        intent_viz.columns = None
        result = await self.chat_service._generate_visualizations_from_intent(
            intent_viz, self.sample_df, "test_file_id", analyze_instance
        )
        
        assert len(result) == 1  # Should still work with auto-detected columns
        
        # Test analysis intent
        intent_analysis = UserIntent(
            intent=IntentType.ANALYSIS, 
            confidence=0.9, 
            entities={}, 
            parameters={}
        )
        
        analyze_instance.generate_visualizations.return_value = [viz_mock, viz_mock]
        
        result = await self.chat_service._generate_visualizations_from_intent(
            intent_analysis, self.sample_df, "test_file_id", analyze_instance
        )
        
        assert len(result) == 2

    # Sửa test này để coi _create_chart_from_type đúng cách (không phải coroutine)
    def test_create_bar_chart(self):
        """Test hàm _create_bar_chart"""
        # Test với một column
        chart = self.chat_service._create_bar_chart(
            self.sample_df, ["category_col"], "Bar Chart Test", {}
        )
        
        assert chart.type == ChartType.BAR
        assert chart.title == "Bar Chart Test"
        assert len(chart.data) == 3  # A, B, C categories
        
        # Test với hai columns
        chart = self.chat_service._create_bar_chart(
            self.sample_df, ["category_col", "numeric_col"], "Bar Chart Test", {}
        )
        
        assert chart.type == ChartType.BAR
        assert len(chart.data) == 5  # Một row cho mỗi data point
    
    def test_create_line_chart(self):
        """Test hàm _create_line_chart"""
        # Test với một column
        chart = self.chat_service._create_line_chart(
            self.sample_df, ["numeric_col"], "Line Chart Test", {}
        )
        
        assert chart.type == ChartType.LINE
        assert chart.title == "Line Chart Test"
        assert len(chart.data) == 5
        
        # Test với nhiều columns
        chart = self.chat_service._create_line_chart(
            self.sample_df, ["category_col", "numeric_col"], "Line Chart Test", {}
        )
        
        assert chart.type == ChartType.LINE
        assert len(chart.data) == 5
    
    def test_create_scatter_chart(self):
        """Test hàm _create_scatter_chart"""
        chart = self.chat_service._create_scatter_chart(
            self.sample_df, ["numeric_col", "numeric_col"], "Scatter Chart Test", {}
        )
        
        assert chart.type == ChartType.SCATTER
        assert chart.title == "Scatter Chart Test"
        assert len(chart.data) == 5
        
        # Test với dữ liệu không phù hợp
        chart = self.chat_service._create_scatter_chart(
            self.sample_df, ["category_col"], "Scatter Chart Test", {}
        )
        
        assert chart is None
    
    def test_create_pie_chart(self):
        """Test hàm _create_pie_chart"""
        chart = self.chat_service._create_pie_chart(
            self.sample_df, ["category_col"], "Pie Chart Test", {}
        )
        
        assert chart.type == ChartType.PIE
        assert chart.title == "Pie Chart Test"
        assert len(chart.data) == 3  # A, B, C categories
    
    def test_create_histogram_chart(self):
        """Test hàm _create_histogram_chart"""
        chart = self.chat_service._create_histogram_chart(
            self.sample_df, ["numeric_col"], "Histogram Test", {}
        )
        
        assert chart.type == ChartType.BAR  # Histogram được render dưới dạng bar chart
        assert chart.title == "Histogram Test"
        assert len(chart.data) > 0
        
        # Test với bins parameter
        chart = self.chat_service._create_histogram_chart(
            self.sample_df, ["numeric_col"], "Histogram Test", {"bins": 3}
        )
        
        assert len(chart.data) == 3  # 3 bins