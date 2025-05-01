import json, os, logging
from typing import Dict, Any
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class ModelConfig:
    def __init__(self):
        self.config_path = os.environ.get("MODEL_CONFIG_PATH", "configs/model_config.json")
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load config from file"""
        try:
            with open(self.config_path, "r") as f:
                logger.info(f"Loaded configuration from {self.config_path} successfully")
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}", exc_info=e)
            raise
        
    def get_model_config(self) -> Dict[str, Any]:
        return self.config.get("model", {})
    
    def get_inference_config(self) -> Dict[str, Any]:
        return self.config.get("inference", {})
        
    def get_data_processing_config(self) -> Dict[str, Any]:
        return self.config.get("data_processing", {})

    def get_visualization_config(self) -> Dict[str, Any]:
        return self.config.get("visualization", {})
    
    def get_cache_config(self) -> Dict[str, Any]:
        return self.config.get("cache", {})
    
    def get_upload_dir(self) -> str:
        return self.config.get("upload_dir", "../storage/uploads")
    
    def get_performance_config(self) -> Dict[str, Any]:
        return self.config.get("performance", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        return self.config.get("logging", {})