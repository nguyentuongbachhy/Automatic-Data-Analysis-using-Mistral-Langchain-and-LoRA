"""
Module mẫu LLM đơn giản hóa, tập trung vào Mistral và loại bỏ các factory pattern phức tạp.
"""
import logging
import os
from typing import Dict, Optional, Any

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Quản lý việc tải mô hình và cấu hình.
    Đơn giản hóa từ các module factory.py và loader.py
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls, config: Optional[Dict[str, Any]] = None):
        """Singleton pattern để tránh tải nhiều mô hình"""
        if cls._instance is None:
            cls._instance = ModelManager(config)
        return cls._instance
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Khởi tạo với config tùy chọn"""
        # Tải config
        self.config = config

        # Khởi tạo các thành phần
        self.model = None
        self.tokenizer = None
        
        # Theo dõi trạng thái tải
        self.is_loaded = False
        self.is_loading = False
        
        logger.info("ModelManager initialized")
    
    def load_model(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Tải mô hình từ hugging face hoặc local.
        
        Args:
            force_reload: Có tải lại mô hình nếu đã tải không
            
        Returns:
            Dict: Chứa model, tokenizer và config
        """
        # Nếu đã tải và không cần tải lại
        if self.is_loaded and not force_reload:
            return {
                "model": self.model,
                "tokenizer": self.tokenizer,
                "config": self.config.get("model", {})
            }
        
        # Nếu đang tải
        if self.is_loading:
            logger.info("Model is already being loaded, waiting...")
            # Đợi đến khi tải xong
            while self.is_loading:
                import time
                time.sleep(0.5)
            return {
                "model": self.model,
                "tokenizer": self.tokenizer,
                "config": self.config.get("model", {})
            }
        
        # Đánh dấu đang tải
        self.is_loading = True
        
        try:
            model_config: Dict[str, Any] = self.config.get("model", {})
            
            base_model_id = model_config.get("base_model_id", "mistralai/Mistral-7B-v0.1")
            base_model_path = model_config.get("base_model_path", "models/base")
            peft_model_path = model_config.get("peft_model_path")
            finetuned_model_path = model_config.get("finetuned_model_path")
            
            local_model_path = os.path.join(base_model_path, os.path.basename(base_model_id))
            model_exists_locally = os.path.exists(local_model_path)
            
            model_path = base_model_id

            load_in_4bit = model_config.get("load_in_4bit", True)
            use_flash_attention = model_config.get("use_flash_attention", False)
            
            # Cấu hình lượng tử hóa để tiết kiệm bộ nhớ
            if load_in_4bit:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
            else:
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                    bnb_8bit_compute_dtype=torch.float16
                )

            logger.info(f"Loading tokenizer from {model_path}")
            tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                padding_side="left",
                trust_remote_code=True,
            )
            tokenizer.pad_token = tokenizer.eos_token
            
            # Các tham số cho mô hình
            model_kwargs = {
                "device_map": model_config.get("device", "auto"),
                "quantization_config": quantization_config,
                "torch_dtype": torch.float16,
                "low_cpu_mem_usage": True,
                "trust_remote_code": True,
            }

            if use_flash_attention:
                model_kwargs["use_flash_attention_2"] = True
            
            logger.info(f"Loading model from {model_path}")

            # Tải từ finetuned path nếu có
            if finetuned_model_path and os.path.exists(finetuned_model_path):
                logger.info(f"Loading finetuned model from {finetuned_model_path}")
                model = AutoModelForCausalLM.from_pretrained(
                    finetuned_model_path,
                    **model_kwargs
                )
            else:
                model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    **model_kwargs
                )
            
            # Tải adapter LoRA nếu có
            lora_config = model_config.get("lora_config", {})
            if lora_config.get("enabled", False) and peft_model_path and os.path.exists(peft_model_path):
                try:
                    from peft import PeftModel
                    logger.info(f"Loading LoRA adapter from {peft_model_path}")
                    model = PeftModel.from_pretrained(model, peft_model_path)
                    logger.info("LoRA adapter loaded successfully")
                except Exception as lora_error:
                    logger.error(f"Error loading LoRA adapter: {str(lora_error)}")
            
            # Lưu mô hình vào local nếu chưa có
            if not model_exists_locally and model_path == base_model_id:
                logger.info(f"Saving model to {local_model_path}")
                os.makedirs(base_model_path, exist_ok=True)
                model.save_pretrained(local_model_path, safe_serialization=True)
                tokenizer.save_pretrained(local_model_path)
            
            # Đặt mô hình ở chế độ evaluation
            model.eval()
            
            # Lưu vào biến instance
            self.model = model
            self.tokenizer = tokenizer
            self.is_loaded = True
            
            logger.info("Model loaded successfully")
            
            return {
                "model": model,
                "tokenizer": tokenizer,
                "config": model_config
            }
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}", exc_info=True)
            raise
        finally:
            # Đánh dấu đã tải xong (dù thành công hay thất bại)
            self.is_loading = False
    
    def get_model_attributes(self):
        """Lấy các thuộc tính của model cho KV cache"""
        if not self.is_model_available:
            self.load_model()
        
        # Lấy thông tin về model để tính toán KV cache
        model = self.model
        model_config = getattr(model.config, "to_dict", lambda: model.config)()
        
        return {
            "n_layers": model_config.get("num_hidden_layers", model_config.get("n_layer", 32)),
            "n_heads": model_config.get("num_attention_heads", model_config.get("n_head", 32)),
            "hidden_size": model_config.get("hidden_size", 4096),
            "head_dim": model_config.get("hidden_size", 4096) // model_config.get("num_attention_heads", 32),
        }
    
    def unload_model(self):
        """Giải phóng bộ nhớ bằng cách hủy model"""
        if self.model is not None:
            del self.model
            import gc
            gc.collect()
            torch.cuda.empty_cache()
            self.model = None
            self.is_loaded = False
            logger.info("Model unloaded")
    
    @property
    def is_model_available(self) -> bool:
        """Check xem model đã sẵn sàng chưa"""
        return self.is_loaded and self.model is not None and self.tokenizer is not None