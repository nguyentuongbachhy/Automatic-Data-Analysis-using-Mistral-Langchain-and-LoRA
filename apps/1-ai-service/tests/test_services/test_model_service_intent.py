import pytest
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np
import json

from app.services.model_service import ModelService
from app.models.chat import ChatMessage, UserIntent, IntentType
from app.core.cache import InferenceCache


class TestModelServiceIntentDetection:
    """Tests cho chức năng Intent Detection của ModelService"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up cho tests"""
        # Tạo mock model và inference engine
        self.model_mock = MagicMock()
        self.inference_engine_mock = MagicMock()
        self.config_mock = MagicMock()
        
        # Patch các dependencies
        with patch('app.services.model_service.ModelService._model', self.model_mock):
            with patch('app.services.model_service.ModelService._inference_engine', self.inference_engine_mock):
                with patch('app.services.model_service.ModelService._config', self.config_mock):
                    with patch('app.services.model_service.ModelService._cache', InferenceCache()):
                        # Initialize ModelService
                        self.model_service = ModelService.get_instance()
                        
                        # Sample data
                        self.sample_df = pd.DataFrame({
                            'numeric_col': [1, 2, 3, 4, 5],
                            'category_col': ['A', 'B', 'A', 'C', 'B'],
                            'date_col': pd.date_range(start='2023-01-01', periods=5)
                        })
                        
                        self.sample_messages = [
                            ChatMessage(role="user", content="Hello"),
                            ChatMessage(role="assistant", content="Hi there")
                        ]
                        
                        yield

    def test_detect_intent_question(self):
        """Test phát hiện intent dạng QUESTION"""
        # Set up mock response cho LLM
        question_response = """```json
        {
            "intent": "question",
            "confidence": 0.95,
            "entities": {},
            "parameters": {}
        }
        ```"""
        self.inference_engine_mock.generate.return_value = question_response
        
        # Call method
        intent = self.model_service.detect_intent(
            "What is the average of numeric_col?", 
            self.sample_messages, 
            self.sample_df
        )
        
        # Verify
        assert intent.intent == IntentType.QUESTION
        assert intent.confidence > 0.9
        assert intent.visualization_type is None
        assert intent.columns is None

    def test_detect_intent_visualization(self):
        """Test phát hiện intent dạng VISUALIZATION"""
        # Set up mock response cho LLM
        viz_response = """```json
        {
            "intent": "visualization",
            "confidence": 0.92,
            "entities": {"chart_type": "bar"},
            "parameters": {"group_by": "category_col"},
            "visualization_type": "bar",
            "columns": ["numeric_col", "category_col"]
        }
        ```"""
        self.inference_engine_mock.generate.return_value = viz_response
        
        # Call method
        intent = self.model_service.detect_intent(
            "Create a bar chart of numeric_col grouped by category_col", 
            self.sample_messages, 
            self.sample_df
        )
        
        # Verify
        assert intent.intent == IntentType.VISUALIZATION
        assert intent.confidence > 0.9
        assert intent.visualization_type == "bar"
        assert intent.columns == ["numeric_col", "category_col"]

    def test_detect_intent_analysis(self):
        """Test phát hiện intent dạng ANALYSIS"""
        # Set up mock response cho LLM
        analysis_response = """```json
        {
            "intent": "analysis",
            "confidence": 0.88,
            "entities": {},
            "parameters": {"comprehensive": true}
        }
        ```"""
        self.inference_engine_mock.generate.return_value = analysis_response
        
        # Call method
        intent = self.model_service.detect_intent(
            "Analyze this dataset in depth", 
            self.sample_messages, 
            self.sample_df
        )
        
        # Verify
        assert intent.intent == IntentType.ANALYSIS
        assert intent.confidence > 0.8
        assert "comprehensive" in intent.parameters

    def test_detect_intent_prediction(self):
        """Test phát hiện intent dạng PREDICTION"""
        # Set up mock response cho LLM
        prediction_response = """```json
        {
            "intent": "prediction",
            "confidence": 0.85,
            "entities": {"target": "numeric_col"},
            "parameters": {"periods": 5},
            "columns": ["date_col", "numeric_col"]
        }
        ```"""
        self.inference_engine_mock.generate.return_value = prediction_response
        
        # Call method
        intent = self.model_service.detect_intent(
            "Predict numeric_col for the next 5 periods", 
            self.sample_messages, 
            self.sample_df
        )
        
        # Verify
        assert intent.intent == IntentType.PREDICTION
        assert intent.confidence > 0.8
        assert intent.columns == ["date_col", "numeric_col"]
        assert intent.parameters.get("periods") == 5

    def test_detect_intent_unknown(self):
        """Test phát hiện intent không rõ ràng"""
        # Set up mock response cho LLM
        unknown_response = "This is not a valid JSON response"
        self.inference_engine_mock.generate.return_value = unknown_response
        
        # Call method
        intent = self.model_service.detect_intent(
            "Something ambiguous", 
            self.sample_messages, 
            None
        )
        
        # Verify
        assert intent.intent == IntentType.UNKNOWN
        assert intent.confidence == 0.1

    def test_detect_intent_with_malformed_json(self):
        """Test phát hiện intent với JSON không hợp lệ"""
        # Set up mock response cho LLM với JSON lỗi cú pháp
        bad_json_response = """```json
        {
            "intent": "visualization",
            "confidence": 0.9,
            "entities": {
            "parameters": {},
        }
        ```"""
        self.inference_engine_mock.generate.return_value = bad_json_response
        
        # Call method
        intent = self.model_service.detect_intent(
            "Show me a chart please", 
            self.sample_messages, 
            self.sample_df
        )
        
        # Verify
        assert intent.intent == IntentType.UNKNOWN
        assert intent.confidence == 0.1

    def test_detect_intent_caching(self):
        """Test cache hoạt động đúng cho intent detection"""
        # Set up mock response cho LLM
        question_response = """```json
        {
            "intent": "question",
            "confidence": 0.95,
            "entities": {},
            "parameters": {}
        }
        ```"""
        self.inference_engine_mock.generate.return_value = question_response
        
        # Call method lần đầu
        intent1 = self.model_service.detect_intent(
            "What is the average of numeric_col?", 
            self.sample_messages, 
            self.sample_df
        )
        
        # Thay đổi mock response
        viz_response = """```json
        {
            "intent": "visualization",
            "confidence": 0.92,
            "visualization_type": "bar",
            "columns": ["numeric_col", "category_col"]
        }
        ```"""
        self.inference_engine_mock.generate.return_value = viz_response
        
        # Call method lần thứ hai với cùng input
        intent2 = self.model_service.detect_intent(
            "What is the average of numeric_col?", 
            self.sample_messages, 
            self.sample_df
        )
        
        # Verify cache hoạt động - cả hai kết quả phải giống nhau
        assert intent1.intent == intent2.intent
        assert intent1.confidence == intent2.confidence
        
        # Verify generate chỉ được gọi một lần
        assert self.inference_engine_mock.generate.call_count == 1