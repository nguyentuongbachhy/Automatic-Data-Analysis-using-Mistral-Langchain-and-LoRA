import pytest
import pandas as pd
import json
from unittest.mock import patch, MagicMock
from app.services.model_service import ModelService
from app.core.cache import InferenceCache
from app.models.chat import UserIntent


class TestModelService:
    """Test model service"""
    
    def setup_method(self):
        """Setup trước mỗi test"""
        # Patch InferenceEngine để không load model thực sự
        self.inference_engine_patcher = patch('ml.model.inference.InferenceEngine')
        self.inference_engine_mock = self.inference_engine_patcher.start()
        self.inference_engine_instance = MagicMock()
        self.inference_engine_mock.return_value = self.inference_engine_instance
        
        # Patch ModelConfig
        self.config_patcher = patch('app.core.config.ModelConfig')
        self.config_mock = self.config_patcher.start()
        self.config_instance = MagicMock()
        self.config_instance.get_inference_config.return_value = {
            "default_temperature": 0.7,
            "default_max_tokens": 512,
            "default_top_p": 0.9,
            "cache_enabled": True,
            "cache_ttl_seconds": 3600
        }
        self.config_mock.return_value = self.config_instance
        
        # Mock model
        self.model_mock = MagicMock()
        ModelService._model = self.model_mock
        ModelService._inference_engine = self.inference_engine_instance
        ModelService._config = self.config_instance
        ModelService._cache = InferenceCache()
        
        # Khởi tạo ModelService
        self.service = ModelService.get_instance()
    
    def teardown_method(self):
        """Teardown sau mỗi test"""
        self.inference_engine_patcher.stop()
        self.config_patcher.stop()
        
        # Reset static variables
        ModelService._instance = None
        ModelService._model = None
        ModelService._inference_engine = None
        ModelService._config = None
        ModelService._cache = None
    
    def test_get_instance(self):
        """Test get instance trả về cùng một instance"""
        instance1 = ModelService.get_instance()
        instance2 = ModelService.get_instance()
        
        assert instance1 is instance2
    
    def test_get_cache_key(self):
        """Test tạo cache key từ prompt và parameters"""
        prompt = "Test prompt"
        
        # Gọi phương thức cần test
        key1 = self.service._get_cache_key(prompt, param1="value1")
        key2 = self.service._get_cache_key(prompt, param1="value1")
        key3 = self.service._get_cache_key(prompt, param1="value2")
        
        # Kiểm tra kết quả
        assert key1 == key2  # Cùng parameters phải tạo ra cùng key
        assert key1 != key3  # Khác parameters phải tạo ra khác key
    
    def test_generate_text(self):
        """Test tạo text từ prompt"""
        # Setup return value cho inference engine
        self.inference_engine_instance.generate.return_value = "This is a test response."
        
        # Gọi phương thức cần test
        response = self.service.generate_text("Test prompt")
        
        # Kiểm tra kết quả
        assert response == "This is a test response."
        
        # Kiểm tra phương thức generate của inference engine được gọi với đúng parameters
        self.inference_engine_instance.generate.assert_called_once()
        args, kwargs = self.inference_engine_instance.generate.call_args
        assert kwargs["prompt"] == "Test prompt"
        assert kwargs["temperature"] == 0.7
        assert kwargs["max_new_tokens"] == 512
        assert kwargs["top_p"] == 0.9
    
    def test_generate_text_with_cache(self):
        """Test tạo text từ prompt với cache"""
        # Setup return value cho inference engine
        self.inference_engine_instance.generate.return_value = "This is a test response."
        
        # Gọi phương thức lần đầu
        response1 = self.service.generate_text("Test prompt")
        
        # Reset mock để kiểm tra xem lần thứ hai có gọi lại không
        self.inference_engine_instance.generate.reset_mock()
        
        # Gọi phương thức lần thứ hai với cùng prompt
        response2 = self.service.generate_text("Test prompt")
        
        # Kiểm tra kết quả
        assert response1 == response2
        
        # Kiểm tra phương thức generate của inference engine không được gọi lần thứ hai
        self.inference_engine_instance.generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_text_stream(self):
        """Test stream text từ prompt"""
        # Setup async generator cho inference engine stream
        async def mock_stream(*args, **kwargs):
            yield "This "
            yield "is "
            yield "a "
            yield "test "
            yield "response."
        
        self.inference_engine_instance.stream = mock_stream
        
        # Gọi phương thức cần test
        chunks = []
        async for chunk in self.service.generate_text_stream("Test prompt"):
            chunks.append(chunk)
        
        # Kiểm tra kết quả
        assert chunks == ["This ", "is ", "a ", "test ", "response."]
    
    def test_detect_intent(self):
        """Test phát hiện intent từ query"""
        # Setup return value cho inference engine
        self.inference_engine_instance.generate.return_value = json.dumps({
            "intent": "visualization",
            "confidence": 0.9,
            "entities": {},
            "parameters": {"chart_type": "bar"}
        })
        
        # Tạo DataFrame test
        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['a', 'b', 'c']
        })
        
        # Gọi phương thức cần test
        intent = self.service.detect_intent("Show me a bar chart", [], df)
        
        # Kiểm tra kết quả
        assert isinstance(intent, UserIntent)
        assert intent.intent == "visualization"
        assert intent.confidence == 0.9
        assert intent.parameters == {"chart_type": "bar"}
        
        # Kiểm tra phương thức generate của inference engine được gọi
        self.inference_engine_instance.generate.assert_called_once()
    
    def test_clear_cache(self):
        """Test xóa cache"""
        # Thêm một số item vào cache
        self.service.cache.set("key1", "value1")
        self.service.cache.set("key2", "value2")
        
        # Kiểm tra cache có dữ liệu
        assert self.service.cache.get("key1") == "value1"
        
        # Gọi phương thức cần test
        self.service.clear_cache()
        
        # Kiểm tra cache đã bị xóa
        assert self.service.cache.get("key1") is None
        assert self.service.cache.get("key2") is None