import logging
import json
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(config_path=None, default_level=logging.INFO):
    """Setup logging configuration"""
    
    if config_path and os.path.exists(config_path):
        with open(config_path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        # Fallback logging configuration
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        handlers = {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": log_dir / "ai-service.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": log_dir / "error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            }
        }
        
        formatters = {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
            }
        }
        
        logging.basicConfig(
            level=default_level,
            format=formatters["standard"]["format"],
            handlers=[
                logging.StreamHandler(sys.stdout),
                RotatingFileHandler(
                    log_dir / "ai-service.log",
                    maxBytes=10485760,
                    backupCount=5
                )
            ]
        )

class PerformanceLogger:
    """Utility for logging performance metrics"""
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.timers = {}
    
    def start_timer(self, action):
        """Start timing an action"""
        self.timers[action] = time.time()
        
    def stop_timer(self, action, extra_data=None):
        """Stop timing an action and log elapsed time"""
        if action not in self.timers:
            self.logger.warning(f"Timer for '{action}' was not started")
            return
        
        elapsed = time.time() - self.timers[action]
        
        log_data = {
            "action": action,
            "elapsed_ms": round(elapsed * 1000, 2)
        }
        
        if extra_data:
            log_data.update(extra_data)
            
        self.logger.info(f"Performance: {json.dumps(log_data)}")
        del self.timers[action]