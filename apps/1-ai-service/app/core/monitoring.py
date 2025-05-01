import time
import logging
import threading
import os
from typing import Dict, Any
import psutil

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Hệ thống monitoring hiệu suất cho AI service"""

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = PerformanceMonitor()
        return cls._instance
    
    def __init__(self, sampling_interval: int = 30):
        """Khởi tạo performance monitor"""
        self.sampling_interval = sampling_interval  # seconds
        self.stats = {
            "memory_usage": [],
            "cpu_usage": [],
            "gpu_usage": [],
            "requests": {
                "total": 0,
                "success": 0,
                "error": 0,
                "latency": [],
                "latency_p95": 0,
                "latency_p50": 0
            },
            "model": {
                "inference_count": 0,
                "tokens_generated": 0,
                "avg_tokens_per_second": 0,
                "max_tokens_per_second": 0,
                "memory_peak": 0
            },
            "system": {
                "start_time": time.time(),
                "last_check": time.time(),
                "host": os.uname().nodename if hasattr(os, 'uname') else 'unknown'
            }
        }

        self._init_system_info()

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        logger.info("Performance monitor initialized")
    
    def _init_system_info(self):
        """Khởi tạo thông tin hệ thống"""
        try:
            # Thông tin CPU
            cpu_info = {
                "count_physical": psutil.cpu_count(logical=False),
                "count_logical": psutil.cpu_count(logical=True),
            }
            
            # Thông tin memory
            memory = psutil.virtual_memory()
            memory_info = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2)
            }
            
            # Thông tin GPU nếu có
            gpu_info = []
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_info = []
                    for i in range(torch.cuda.device_count()):
                        props = torch.cuda.get_device_properties(i)
                        gpu_info.append({
                            "device": i,
                            "name": props.name,
                            "memory_total_gb": round(props.total_memory / (1024**3), 2)
                        })
            except Exception as e:
                logger.debug(f"GPU info unavailable: {str(e)}")
                
            # Thêm thông tin vào stats
            self.stats["system"]["cpu"] = cpu_info
            self.stats["system"]["memory"] = memory_info
            self.stats["system"]["gpu"] = gpu_info
            
        except Exception as e:
            logger.error(f"Error initializing system info: {str(e)}")

    def _monitor_loop(self):
        """Background thread to collect system metrics"""
        while self.running:
            try:
                # CPU và memory
                self.stats["cpu_usage"].append(psutil.cpu_percent(interval=1))
                self.stats["memory_usage"].append(psutil.virtual_memory().percent)
                
                # GPU
                try:
                    import torch
                    if torch.cuda.is_available():
                        gpu_stats = []
                        for i in range(torch.cuda.device_count()):
                            gpu_stats.append({
                                "device": i,
                                "memory_allocated_gb": round(torch.cuda.memory_allocated(i) / (1024**3), 2),
                                "memory_reserved_gb": round(torch.cuda.memory_reserved(i) / (1024**3), 2),
                                "utilization": torch.cuda.utilization(i) if hasattr(torch.cuda, 'utilization') else None
                            })
                        self.stats["gpu_usage"].append(gpu_stats)
                        
                        # Theo dõi memory cao nhất được sử dụng
                        if gpu_stats and "memory_allocated_gb" in gpu_stats[0]:
                            current_mem = gpu_stats[0]["memory_allocated_gb"]
                            self.stats["model"]["memory_peak"] = max(
                                self.stats["model"]["memory_peak"], 
                                current_mem
                            )
                except Exception as e:
                    pass
                
                # Giới hạn kích thước dữ liệu lịch sử
                max_history = 60 * 24  # 1 ngày nếu interval là 1 phút
                self.stats["cpu_usage"] = self.stats["cpu_usage"][-max_history:]
                self.stats["memory_usage"] = self.stats["memory_usage"][-max_history:]
                if "gpu_usage" in self.stats:
                    self.stats["gpu_usage"] = self.stats["gpu_usage"][-max_history:]
                
                # Cập nhật thời gian kiểm tra
                self.stats["system"]["last_check"] = time.time()
                
                # Cập nhật percentiles cho latency
                if len(self.stats["requests"]["latency"]) > 0:
                    latencies = sorted(self.stats["requests"]["latency"])
                    p95_idx = int(len(latencies) * 0.95)
                    p50_idx = int(len(latencies) * 0.5)
                    
                    self.stats["requests"]["latency_p95"] = latencies[p95_idx]
                    self.stats["requests"]["latency_p50"] = latencies[p50_idx]
                
                # Ngủ
                time.sleep(self.sampling_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring thread: {str(e)}")
                time.sleep(5)  # Ngủ ngắn hơn khi có lỗi

    def record_request(self, duration: float, success: bool = True, endpoint: str = "unknown"):
        """Ghi nhận request metrics"""
        self.stats["requests"]["total"] += 1
        if success:
            self.stats["requests"]["success"] += 1
        else:
            self.stats["requests"]["error"] += 1
            
        self.stats["requests"]["latency"].append(duration)
        
        # Giới hạn kích thước danh sách latency
        max_latency_history = 1000
        if len(self.stats["requests"]["latency"]) > max_latency_history:
            self.stats["requests"]["latency"] = self.stats["requests"]["latency"][-max_latency_history:]
        
        # Cập nhật endpoint-specific stats nếu follow-up
        if "endpoints" not in self.stats["requests"]:
            self.stats["requests"]["endpoints"] = {}
            
        if endpoint not in self.stats["requests"]["endpoints"]:
            self.stats["requests"]["endpoints"][endpoint] = {
                "count": 0,
                "success": 0,
                "error": 0,
                "latency_sum": 0
            }
            
        self.stats["requests"]["endpoints"][endpoint]["count"] += 1
        if success:
            self.stats["requests"]["endpoints"][endpoint]["success"] += 1
        else:
            self.stats["requests"]["endpoints"][endpoint]["error"] += 1
            
        self.stats["requests"]["endpoints"][endpoint]["latency_sum"] += duration

    def record_inference(self, tokens_generated: int, duration: float):
        """Ghi nhận model inference metrics"""
        self.stats["model"]["inference_count"] += 1
        self.stats["model"]["tokens_generated"] += tokens_generated
        
        # Tính tokens per second
        tokens_per_second = tokens_generated / duration if duration > 0 else 0
        
        # Cập nhật max tokens per second
        self.stats["model"]["max_tokens_per_second"] = max(
            self.stats["model"]["max_tokens_per_second"],
            tokens_per_second
        )
        
        # Cập nhật average tokens per second với weighted average
        count = self.stats["model"]["inference_count"]
        avg_tps = self.stats["model"]["avg_tokens_per_second"]
        
        if count > 1:
            # Weighted average with more weight for recent values
            self.stats["model"]["avg_tokens_per_second"] = (
                (avg_tps * (count - 1) * 0.9 + tokens_per_second) / (count * 0.9)
            )
        else:
            self.stats["model"]["avg_tokens_per_second"] = tokens_per_second

    def record_chat_processing(self, duration: float):
        """
        Record metrics specific to chat message processing
        
        Args:
            duration: Time taken to process the chat message in seconds
        """
        # Add chat processing specific tracking to request metrics
        if "chat_processing" not in self.stats["requests"]:
            self.stats["requests"]["chat_processing"] = {
                "count": 0,
                "total_duration": 0,
                "avg_duration": 0,
                "max_duration": 0
            }
        
        chat_stats = self.stats["requests"]["chat_processing"]
        
        chat_stats["count"] += 1
        chat_stats["total_duration"] += duration
        chat_stats["avg_duration"] = chat_stats["total_duration"] / chat_stats["count"]
        chat_stats["max_duration"] = max(chat_stats["max_duration"], duration)

    def record_visualization_generation(self, visualizations_count: int):
        """
        Record metrics for visualization generation
        
        Args:
            visualizations_count: Number of visualizations generated
        """
        # Initialize visualization generation stats if not exists
        if "visualization_generation" not in self.stats["requests"]:
            self.stats["requests"]["visualization_generation"] = {
                "count": 0,
                "total_visualizations": 0,
                "max_visualizations_per_gen": 0
            }
        
        viz_stats = self.stats["requests"]["visualization_generation"]
        
        viz_stats["count"] += 1
        viz_stats["total_visualizations"] += visualizations_count
        viz_stats["max_visualizations_per_gen"] = max(
            viz_stats["max_visualizations_per_gen"], 
            visualizations_count
        )
        viz_stats["avg_visualizations_per_gen"] = (
            viz_stats["total_visualizations"] / viz_stats["count"]
        )

    def record_insight_generation(self, insights_count: int):
        """
        Record metrics for insight generation
        
        Args:
            insights_count: Number of insights generated
        """
        # Initialize insight generation stats if not exists
        if "insight_generation" not in self.stats["requests"]:
            self.stats["requests"]["insight_generation"] = {
                "count": 0,
                "total_insights": 0,
                "max_insights_per_gen": 0
            }
        
        insight_stats = self.stats["requests"]["insight_generation"]
        
        insight_stats["count"] += 1
        insight_stats["total_insights"] += insights_count
        insight_stats["max_insights_per_gen"] = max(
            insight_stats["max_insights_per_gen"], 
            insights_count
        )
        insight_stats["avg_insights_per_gen"] = (
            insight_stats["total_insights"] / insight_stats["count"]
        )

    def record_error(self, error_type: str, error_message: str = None):
        """
        Record error metrics for different types of errors
        
        Args:
            error_type: Type or source of the error (e.g., "chat_message", "model_inference")
            error_message: Optional detailed error message
        """
        # Initialize errors tracking if not exists
        if "errors" not in self.stats:
            self.stats["errors"] = {}
        
        # Track error by type
        if error_type not in self.stats["errors"]:
            self.stats["errors"][error_type] = {
                "count": 0,
                "recent_errors": []
            }
        
        error_stats = self.stats["errors"][error_type]
        error_stats["count"] += 1
        
        # Store recent error details (limit to last 10)
        if error_message:
            error_stats["recent_errors"].append({
                "timestamp": time.time(),
                "message": error_message
            })
            
            if len(error_stats["recent_errors"]) > 10:
                error_stats["recent_errors"] = error_stats["recent_errors"][-10:]

        # Ensure errors are tracked in the requests statistics as well
        if "errors" not in self.stats["requests"]:
            self.stats["requests"]["errors"] = 0
        self.stats["requests"]["errors"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Lấy tất cả metrics hiện tại"""
        current_stats = {
            "system": {
                "uptime_seconds": time.time() - self.stats["system"]["start_time"],
                "host": self.stats["system"]["host"],
                "cpu": self.stats["system"].get("cpu", {}),
                "memory": self.stats["system"].get("memory", {})
            },
            "current": {
                "cpu": {
                    "current": self.stats["cpu_usage"][-1] if self.stats["cpu_usage"] else 0,
                    "avg_5min": sum(self.stats["cpu_usage"][-5:]) / min(5, len(self.stats["cpu_usage"])) if self.stats["cpu_usage"] else 0
                },
                "memory": {
                    "current": self.stats["memory_usage"][-1] if self.stats["memory_usage"] else 0,
                    "avg_5min": sum(self.stats["memory_usage"][-5:]) / min(5, len(self.stats["memory_usage"])) if self.stats["memory_usage"] else 0
                },
                "gpu": self.stats["gpu_usage"][-1] if self.stats.get("gpu_usage", []) else None
            },
            "requests": {
                "total": self.stats["requests"]["total"],
                "success": self.stats["requests"]["success"],
                "error": self.stats["requests"]["error"],
                "success_rate": (
                    self.stats["requests"]["success"] / self.stats["requests"]["total"] * 100
                    if self.stats["requests"]["total"] > 0 else 100
                ),
                "latency_avg": (
                    sum(self.stats["requests"]["latency"]) / len(self.stats["requests"]["latency"])
                    if self.stats["requests"]["latency"] else 0
                ),
                "latency_p95": self.stats["requests"]["latency_p95"],
                "latency_p50": self.stats["requests"]["latency_p50"]
            },
            "model": {
                "inference_count": self.stats["model"]["inference_count"],
                "tokens_generated": self.stats["model"]["tokens_generated"],
                "avg_tokens_per_second": self.stats["model"]["avg_tokens_per_second"],
                "max_tokens_per_second": self.stats["model"]["max_tokens_per_second"],
                "memory_peak_gb": self.stats["model"]["memory_peak"]
            }
        }
        
        # Thêm thống kê endpoint nếu có
        if "endpoints" in self.stats["requests"]:
            current_stats["requests"]["endpoints"] = {}
            for endpoint, data in self.stats["requests"]["endpoints"].items():
                current_stats["requests"]["endpoints"][endpoint] = {
                    "count": data["count"],
                    "success_rate": (data["success"] / data["count"] * 100) if data["count"] > 0 else 100,
                    "avg_latency": data["latency_sum"] / data["count"] if data["count"] > 0 else 0
                }
        
        return current_stats
    
    def stop(self):
        """Dừng thread monitoring"""
        self.running = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)