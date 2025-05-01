# app/services/streaming/streaming_manager.py
import asyncio
import json
import re
import logging
import pandas as pd
import time
from typing import AsyncGenerator, Dict, Any, Optional, List, Callable

from sse_starlette.sse import EventSourceResponse

from app.models.chat import IntentType, UserIntent
from app.services.model_service import ModelService
from app.services.chat.chat_service import ChatService
from app.services.analyze_service import AnalyzeService
from app.services.intent_service import IntentDetectionService
from app.services.validation_service import ValidationService

# LangChain integration
from langchain.callbacks.base import BaseCallbackHandler

# Import from ml module
from ml.tools.postgres_connector import PostgreSQLConnector

logger = logging.getLogger(__name__)

class ChainOfThoughtHandler(BaseCallbackHandler):
    """Callback handler for streaming Chain of Thought reasoning"""
    
    def __init__(self, yield_func: Callable[[Dict[str, Any]], None]):
        """Initialize with yield function"""
        self.yield_func = yield_func
        self.thinking_buffer = ""
        self.in_thinking = False
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 15
        
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Run when LLM starts running."""
        pass
    
    def on_llm_new_token(self, token: str, **kwargs):
        """Run on new LLM token."""
        # Check if we're entering thinking mode
        if "<thinking>" in token and not self.in_thinking:
            self.in_thinking = True
            self.thinking_buffer = ""
            self.yield_func({
                "event": "thinking_start",
                "data": json.dumps({"message": "Thinking..."})
            })
            return
            
        # Check if we're exiting thinking mode
        if "</thinking>" in token and self.in_thinking:
            self.in_thinking = False
            # Send the complete thinking buffer
            if self.thinking_buffer:
                self.yield_func({
                    "event": "thinking",
                    "data": json.dumps({"thought": self.thinking_buffer.strip()})
                })
            return
            
        # If in thinking mode, accumulate to buffer
        if self.in_thinking:
            self.thinking_buffer += token
            # Periodically send thinking updates for long chains
            if len(self.thinking_buffer) > 500:
                self.yield_func({
                    "event": "thinking_progress",
                    "data": json.dumps({"thought": self.thinking_buffer.strip()})
                })
                self.thinking_buffer = ""
        else:
            # Normal token output
            self.yield_func({
                "event": "message",
                "data": json.dumps({"token": token, "done": False})
            })
        
        # Send heartbeat if needed
        current_time = time.time()
        if current_time - self.last_heartbeat > self.heartbeat_interval:
            self.yield_func({
                "event": "heartbeat",
                "data": json.dumps({"timestamp": str(current_time)})
            })
            self.last_heartbeat = current_time
    
    def on_llm_end(self, response, **kwargs):
        """Run when LLM ends running."""
        # Send any remaining buffer and signal completion
        if self.thinking_buffer:
            self.yield_func({
                "event": "thinking",
                "data": json.dumps({"thought": self.thinking_buffer.strip()})
            })
            self.thinking_buffer = ""
        
        self.yield_func({
            "event": "message",
            "data": json.dumps({"token": "", "done": True})
        })
    
    def on_llm_error(self, error, **kwargs):
        """Run when LLM errors."""
        self.yield_func({
            "event": "error",
            "data": json.dumps({"error": str(error)})
        })
    
    def on_tool_start(self, serialized, input_str, **kwargs):
        """Run when tool starts running."""
        self.yield_func({
            "event": "tool_start",
            "data": json.dumps({"tool": serialized['name'], "input": input_str})
        })
    
    def on_tool_end(self, output, **kwargs):
        """Run when tool ends running."""
        self.yield_func({
            "event": "tool_end",
            "data": json.dumps({"output": output})
        })
    
    def on_tool_error(self, error, **kwargs):
        """Run when tool errors."""
        self.yield_func({
            "event": "error",
            "data": json.dumps({"error": str(error)})
        })
    
    def on_agent_action(self, action, **kwargs):
        """Run on agent action."""
        self.yield_func({
            "event": "agent_action",
            "data": json.dumps({
                "tool": action.tool,
                "tool_input": action.tool_input,
                "log": action.log
            })
        })
    
    def on_agent_finish(self, finish, **kwargs):
        """Run on agent end."""
        self.yield_func({
            "event": "agent_finish",
            "data": json.dumps({"output": finish.return_values.get('output', '')})
        })


class StreamingManager:
    """Enhanced streaming manager for integrating LangChain with Chain-of-Thought"""
    
    def __init__(
        self,
        model_service: Optional[ModelService] = None,
        chat_service: Optional[ChatService] = None,
        analyze_service: Optional[AnalyzeService] = None,
        intent_service: Optional[IntentDetectionService] = None,
        validation_service: Optional[ValidationService] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize StreamingManager
        
        Args:
            model_service: Model service
            chat_service: Chat service
            analyze_service: Analysis service
            intent_service: Intent detection service 
            validation_service: Validation service
            config: Configuration
        """
        self.connect = PostgreSQLConnector()
        self.model_service = model_service
        self.chat_service = chat_service
        self.analyze_service = analyze_service
        self.intent_service = intent_service
        self.validation_service = validation_service
        
        # Default config
        self._default_config = {
            "heartbeat_interval": 15,  # seconds
            "max_file_size_mb": 100,   # 100MB file size limit
            "stream_chunk_size": 50,   # Chunk size for pandas iterator
            "auto_detect_intent": True,
            "auto_generate_viz": True,
            "viz_confidence_threshold": 0.65,
            "insight_confidence_threshold": 0.65,
            "stream_buffer_size": 10,   # Tokens to buffer before sending
            "retry_attempts": 3,
            "retry_delay": 1.0,
            "enable_telemetry": False,
            "use_langchain": True,     # Use LangChain for reasoning
            "show_thinking": True      # Show Chain-of-Thought reasoning
        }
        
        # Merge config with default
        self._config = self._default_config.copy()
        if config:
            self._config.update(config)
        
        # Heartbeat interval
        self._heartbeat_interval = self._config["heartbeat_interval"]
    
    async def stream_chat_response(
        self,
        file_id: Optional[str] = None,
        file_path: Optional[str] = None,
        query: str = "",
        chat_id: Optional[str] = None,
        message_id: Optional[str] = None,
        include_visualizations: bool = True,
        include_insights: bool = True,
    ) -> EventSourceResponse:
        """
        Stream chat response với xử lý bất đồng bộ tối ưu và Chain-of-Thought reasoning
        """
        async def event_generator() -> AsyncGenerator[Dict[str, Any], None]:
            error_occurred = False
            last_heartbeat = time.time()
            full_response_content = ""  # Thêm dòng này để khởi tạo biến
            
            # Theo dõi metrics
            start_time = time.time()
            metrics = {
                "tokens_generated": 0,
                "processing_time": 0,
                "file_loading_time": 0,
                "model_inference_time": 0
            }
            
            try:
                # Khởi tạo ChatService nếu chưa có
                if not self.chat_service:
                    if self.model_service:
                        self.chat_service = ChatService(
                            model_service=self.model_service,
                            intent_service=self.intent_service,
                            validation_service=self.validation_service
                        )
                    else:
                        self.chat_service = ChatService()
                
                # Gửi sự kiện bắt đầu
                yield {
                    "event": "status",
                    "data": json.dumps({
                        "status": "Đang xử lý yêu cầu của bạn...",
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "progress": 0
                    })
                }
                
                # Đọc file nếu cần
                df = None
                file_start_time = time.time()
                
                if file_id and file_path:
                    try:
                        # Thông báo đang tải file
                        yield {
                            "event": "status",
                            "data": json.dumps({
                                "status": "Đang tải dữ liệu...",
                                "progress": 5,
                                "chat_id": chat_id,
                                "message_id": message_id
                            })
                        }
                        
                        # Task load và validate file với ValidationService
                        if self.validation_service:
                            df, quality_report = await self.validation_service.load_and_validate_data(
                                file_path, sample=True, max_rows=self._config["stream_chunk_size"]
                            )
                        
                        metrics["file_loading_time"] = time.time() - file_start_time
                        
                        if df is not None:
                            file_info = {
                                "rows": len(df),
                                "columns": len(df.columns),
                                "column_names": df.columns.tolist()
                            }
                            
                            # Thêm thông tin chất lượng dữ liệu
                            if quality_report:
                                # Trích xuất thông tin quan trọng
                                quality_summary = {
                                    "overall_score": quality_report.get("data_quality", {}).get("quality_metrics", {}).get("overall_score", 0),
                                    "missing_percent": quality_report.get("data_quality", {}).get("completeness", {}).get("missing_percent", 0),
                                    "duplicates": quality_report.get("data_quality", {}).get("uniqueness", {}).get("duplicate_rows", 0),
                                    "issues": quality_report.get("data_quality", {}).get("issues", [])[:3]  # Lấy tối đa 3 vấn đề
                                }
                                file_info["quality"] = quality_summary
                            
                            yield {
                                "event": "status",
                                "data": json.dumps({
                                    "status": "Dữ liệu đã sẵn sàng!",
                                    "progress": 10,
                                    "chat_id": chat_id,
                                    "message_id": message_id,
                                    "file_info": file_info
                                })
                            }
                            
                            if quality_report and quality_report.get("data_quality", {}).get("quality_metrics", {}).get("overall_score", 100) < 50:
                                yield {
                                    "event": "warning",
                                    "data": json.dumps({
                                        "warning": "Dữ liệu có chất lượng thấp, kết quả phân tích có thể không chính xác",
                                        "chat_id": chat_id,
                                        "message_id": message_id,
                                        "quality_score": quality_report.get("data_quality", {}).get("quality_metrics", {}).get("overall_score", 0)
                                    })
                                }
                        else:
                            yield {
                                "event": "error",
                                "data": json.dumps({
                                    "error": "Không thể tải dữ liệu từ file",
                                    "chat_id": chat_id,
                                    "message_id": message_id
                                })
                            }
                    except Exception as e:
                        logger.error(f"Lỗi khi tải file: {str(e)}", exc_info=True)
                        yield {
                            "event": "error",
                            "data": json.dumps({
                                "error": f"Lỗi khi tải file: {str(e)}",
                                "chat_id": chat_id,
                                "message_id": message_id
                            })
                        }
                        # Tiếp tục xử lý, nhưng không có dataframe
                
                # Phân tích intent
                intent = None
                
                if df is not None and self.intent_service and self._config["auto_detect_intent"]:
                    try:
                        # Thông báo đang phân tích intent
                        yield {
                            "event": "status",
                            "data": json.dumps({
                                "status": "Đang phân tích yêu cầu của bạn...",
                                "progress": 15,
                                "chat_id": chat_id,
                                "message_id": message_id
                            })
                        }
                        
                        # Phát hiện intent
                        intent = await self.intent_service.detect_intent(query, df)
                        
                        # Gửi intent cho client
                        if intent and intent.intent != IntentType.UNKNOWN:
                            intent_type = intent.intent.value if hasattr(intent.intent, 'value') else str(intent.intent)
                            intent_confidence = float(intent.confidence) if hasattr(intent, 'confidence') else 0.0
                            
                            yield {
                                "event": "intent",
                                "data": json.dumps({
                                    "intent": intent_type,
                                    "confidence": intent_confidence,
                                    "columns": intent.columns if hasattr(intent, 'columns') else [],
                                    "visualization_type": intent.visualization_type if hasattr(intent, 'visualization_type') else None,
                                    "chat_id": chat_id,
                                    "message_id": message_id
                                })
                            }
                    except Exception as e:
                        logger.error(f"Lỗi khi phát hiện intent: {str(e)}", exc_info=True)
                        # Tiếp tục mà không có intent
                
                # Khởi tạo các task phân tích bất đồng bộ
                analysis_tasks = {}
                
                # Ưu tiên khởi tạo task visualizations/insights dựa trên intent
                if file_id and file_path and df is not None:
                    self._setup_analysis_tasks(
                        analysis_tasks=analysis_tasks,
                        file_id=file_id,
                        file_path=file_path,
                        df=df,
                        intent=intent,
                        query=query,
                        include_visualizations=include_visualizations,
                        include_insights=include_insights,
                        yield_status=lambda status, progress=0: {
                            "event": "status",
                            "data": json.dumps({
                                "status": status,
                                "progress": progress,
                                "chat_id": chat_id,
                                "message_id": message_id
                            })
                        }
                    )
                
                # Chuẩn bị prompt
                yield {
                    "event": "status",
                    "data": json.dumps({
                        "status": "Đang tạo phản hồi...",
                        "progress": 20,
                        "chat_id": chat_id,
                        "message_id": message_id
                    })
                }
                
                # Lấy system prompt (tương tự như trong prepare_prompt)
                system_prompt = None
                if self.chat_service:
                    system_prompt, _, _ = await self.chat_service.prepare_prompt(query, file_id, file_path)
                
                # Stream inference với Chain-of-Thought reasoning
                model_start_time = time.time()
                content = ""  # Nội dung tích lũy
                
                # ===== Kiểm tra và sử dụng LangChain streaming =====
                use_langchain = self._config.get("use_langchain", True)
                has_langchain_streaming = hasattr(self.model_service, 'stream_langchain_reasoning')
                
                if use_langchain and has_langchain_streaming:
                    logger.info(f"Sử dụng LangChain reasoning stream cho conversation {chat_id}")
                    
                    try:
                        # Tạo streaming callback để yield token thành event
                        async def stream_callback(token, is_done=False):
                            nonlocal content, last_heartbeat, metrics
                            
                            if not token.startswith("<thinking>") and not "</thinking>" in token:
                                full_response_content += token

                            # Update metrics
                            metrics["tokens_generated"] += 1
                            
                            # Thêm token vào content
                            content += token
                            
                            # Heartbeat check
                            current_time = time.time()
                            if current_time - last_heartbeat > self._heartbeat_interval:
                                yield {
                                    "event": "heartbeat",
                                    "data": json.dumps({"timestamp": str(current_time)})
                                }
                                last_heartbeat = current_time
                            
                            # Gửi token
                            if token:  # Chỉ gửi token có nội dung
                                yield {
                                    "event": "message",
                                    "data": json.dumps({
                                        "token": token, 
                                        "chat_id": chat_id, 
                                        "message_id": message_id, 
                                        "done": is_done
                                    })
                                }
                                
                                # Nếu là thinking, gửi trạng thái thinking
                                if "<thinking>" in token and not "</thinking>" in token:
                                    yield {
                                        "event": "thinking_start",
                                        "data": json.dumps({
                                            "chat_id": chat_id,
                                            "message_id": message_id
                                        })
                                    }
                                
                                # Nếu kết thúc thinking, gửi trạng thái thinking_end  
                                if "</thinking>" in token:
                                    yield {
                                        "event": "thinking_end",
                                        "data": json.dumps({
                                            "chat_id": chat_id,
                                            "message_id": message_id
                                        })
                                    }

                                if chat_id and self.connect:
                                    try:
                                        clean_content = re.sub(r'<thinking>.*?</thinking>', '', full_response_content, flags=re.DOTALL).strip()
                                        metadata = {}
                                        if "viz_data" in locals() and viz_data:
                                            metadata["has_visualizations"] = True
                                            metadata["visualizations_count"] = len(viz_data)
                                        if "insight_data" in locals() and insight_data:
                                            metadata["has_insights"] = True
                                            metadata["insights_count"] = len(insight_data)
                                        
                                        # Lưu tin nhắn phản hồi
                                        assistant_message_id = self.chat_service.insert_message(
                                            chat_id=chat_id,
                                            role="ASSISTANT",
                                            content=clean_content,
                                            metadata=metadata
                                        )
                                        
                                        if assistant_message_id:
                                            # Cập nhật lastMessage trong bảng Chat
                                            self.chat_service.update_last_message(chat_id, assistant_message_id)
                                            
                                            # Gửi thông tin về message ID đã lưu
                                            yield {
                                                "event": "db_saved",
                                                "data": json.dumps({
                                                    "chat_id": chat_id,
                                                    "message_id": message_id,
                                                    "assistant_message_id": assistant_message_id
                                                })
                                            }

                                    except Exception as save_err:
                                        logger.error(f"Lỗi khi lưu phản hồi vào database: {str(save_err)}", exc_info=True)
                                        yield {
                                            "event": "warning",
                                            "data": json.dumps({
                                                "warning": f"Không thể lưu phản hồi vào database: {str(save_err)}",
                                                "chat_id": chat_id,
                                                "message_id": message_id
                                            })
                                        }

                            # Xử lý phân tích bổ sung
                            if len(content) > 100 and df is not None and file_id and file_path:
                                self._setup_additional_analysis_tasks(
                                    analysis_tasks=analysis_tasks,
                                    file_id=file_id,
                                    file_path=file_path,
                                    df=df,
                                    content=content,
                                    query=query,
                                    include_visualizations=include_visualizations,
                                    include_insights=include_insights
                                )
                        
                        # Chạy LangChain stream
                        async for token in self.model_service.stream_langchain_reasoning(chat_id, query):
                            # Collect non-thinking tokens for database saving
                            if not token.startswith("<thinking>") and not "</thinking>" in token:
                                full_response_content += token
                            yield token
                            # Small await to not block event loop
                            await asyncio.sleep(0)
                        
                        # Signal completion của text
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "token": "", 
                                "chat_id": chat_id, 
                                "message_id": message_id, 
                                "done": True
                            })
                        }
                        
                    except Exception as e:
                        logger.error(f"Lỗi khi streaming qua LangChain: {str(e)}", exc_info=True)
                        # Thử fallback về cách streaming thông thường
                        yield {
                            "event": "status",
                            "data": json.dumps({
                                "status": "Đang thử phương pháp thay thế...",
                                "progress": 30,
                                "chat_id": chat_id,
                                "message_id": message_id
                            })
                        }
                        
                        # Fallback to traditional streaming method
                        fallback_streaming = True
                    else:
                        fallback_streaming = False
                else:
                    # Không có LangChain streaming
                    fallback_streaming = True
                
                # ===== Fallback: Sử dụng phương pháp streaming thông thường =====
                if fallback_streaming:
                    logger.info(f"Sử dụng phương pháp streaming thông thường")
                    
                    try:
                        # Khởi tạo biến (hoặc đảm bảo nó đã được khởi tạo)
                        full_response_content = ""
                        
                        # Check mistral direct streaming
                        if hasattr(self.model_service, 'mistral') and hasattr(self.model_service.mistral, 'stream'):
                            # Stream từ mistral
                            async for token in self.model_service.mistral.stream(...):
                                # Update metrics
                                metrics["tokens_generated"] += 1
                                
                                # Thêm token vào content và biến tích lũy
                                full_response_content += token
                                content += token
                                
                                # Gửi token
                                yield {
                                    "event": "message",
                                    "data": json.dumps({
                                        "token": token, 
                                        "chat_id": chat_id, 
                                        "message_id": message_id, 
                                        "done": False
                                    })
                                }
                                
                                # Heartbeat check
                                current_time = time.time()
                                if current_time - last_heartbeat > self._heartbeat_interval:
                                    yield {
                                        "event": "heartbeat",
                                        "data": json.dumps({"timestamp": str(current_time)})
                                    }
                                    last_heartbeat = current_time
                                
                                # Xử lý phân tích bổ sung
                                if len(content) > 100 and df is not None and file_id and file_path:
                                    self._setup_additional_analysis_tasks(
                                        analysis_tasks=analysis_tasks,
                                        file_id=file_id,
                                        file_path=file_path,
                                        df=df,
                                        content=content,
                                        query=query,
                                        include_visualizations=include_visualizations,
                                        include_insights=include_insights
                                    )
                                
                                # Nhỏ await để không block event loop
                                await asyncio.sleep(0)
                        
                        else:
                            # Không có phương thức stream trực tiếp - báo lỗi
                            raise ValueError("Không tìm thấy phương thức streaming phù hợp")
                    
                        # Signal completion của text
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "token": "", 
                                "chat_id": chat_id, 
                                "message_id": message_id, 
                                "done": True
                            })
                        }
                        
                    except Exception as e:
                        error_occurred = True
                        logger.error(f"Lỗi trong streaming: {str(e)}", exc_info=True)
                        yield {
                            "event": "error",
                            "data": json.dumps({
                                "error": f"Lỗi streaming: {str(e)}",
                                "chat_id": chat_id,
                                "message_id": message_id
                            })
                        }
                
                # Ghi nhận thời gian inference
                metrics["model_inference_time"] = time.time() - model_start_time
                
                # Xử lý kết quả từ các task visualizations và insights
                if len(analysis_tasks) > 0:
                    viz_data, insight_data = await self._process_analysis_results(
                        analysis_tasks, chat_id, message_id
                    )
                    
                    # Thêm thông tin về visualizations và insights vào metrics
                    if viz_data:
                        metrics["visualizations_count"] = len(viz_data)
                    if insight_data:
                        metrics["insights_count"] = len(insight_data)
                
                # Gửi sự kiện summary với thông tin tổng hợp
                yield {
                    "event": "summary",
                    "data": json.dumps({
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "has_visualizations": "visualizations" in analysis_tasks and analysis_tasks["visualizations"] is not None,
                        "visualizations_count": len(viz_data) if "viz_data" in locals() and viz_data else 0,
                        "has_insights": "insights" in analysis_tasks and analysis_tasks["insights"] is not None,
                        "insights_count": len(insight_data) if "insight_data" in locals() and insight_data else 0
                    })
                }
                
                # Update metrics
                metrics["processing_time"] = time.time() - start_time
                
                # Gửi metrics nếu cần
                if self._config["enable_telemetry"]:
                    yield {
                        "event": "metrics",
                        "data": json.dumps({
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "metrics": metrics
                        })
                    }
                
                # Completion event
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "message": "Xử lý hoàn tất",
                        "processing_time": metrics["processing_time"]
                    })
                }
                
            except Exception as e:
                error_occurred = True
                logger.error(f"Lỗi trong streaming: {str(e)}", exc_info=True)
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": str(e),
                        "chat_id": chat_id,
                        "message_id": message_id
                    })
                }
            finally:
                if error_occurred:
                    yield {
                        "event": "complete",
                        "data": json.dumps({
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "message": "Xử lý bị gián đoạn do lỗi"
                        })
                    }
        
        return EventSourceResponse(event_generator())
    
    def _setup_analysis_tasks(
        self,
        analysis_tasks: Dict[str, Any],
        file_id: Optional[str],
        file_path: Optional[str],
        df: Optional[pd.DataFrame],
        intent: Optional[UserIntent],
        query: str,
        include_visualizations: bool,
        include_insights: bool,
        yield_status: callable
    ) -> None:
        """
        Set up visualization/insight tasks based on intent
        
        Args:
            analysis_tasks: Dict to store tasks
            file_id: File ID
            file_path: File path
            df: DataFrame
            intent: Detected intent
            query: User query
            include_visualizations: Whether to include visualizations
            include_insights: Whether to include insights
            yield_status: Function to yield status events
        """
        # Can't initialize tasks without df or file information
        if not (file_id and file_path and df is not None):
            return
            
        # No intent or unclear intent
        if intent is None or intent.intent == IntentType.UNKNOWN:
            return
        
        intent_type = intent.intent.value if hasattr(intent.intent, 'value') else str(intent.intent)
        intent_confidence = float(intent.confidence) if hasattr(intent, 'confidence') else 0.0
        
        # Create visualization task for visualization/analysis intent
        if (intent_type in ["VISUALIZATION", "ANALYSIS"] and 
            intent_confidence > self._config["viz_confidence_threshold"] and
            include_visualizations):
            
            # Notify visualization creation
            yield_status("Creating visualizations from data...", 25)
            
            # Prepare parameters
            columns_to_use = intent.columns if hasattr(intent, 'columns') else None
            chart_type = intent.visualization_type if hasattr(intent, 'visualization_type') else None
            
            # Create task
            analysis_tasks["visualization_started"] = True
            
            if hasattr(self.chat_service, "generate_visualizations"):
                analysis_tasks["visualizations"] = asyncio.create_task(
                    self.chat_service.generate_visualizations(
                        file_id=file_id,
                        file_path=file_path,
                        content="",
                        query=query,
                        columns=columns_to_use,
                        chart_type=chart_type
                    )
                )
            elif self.analyze_service:
                # Fallback: use analyze_service directly
                analysis_tasks["visualizations"] = asyncio.create_task(
                    self.analyze_service.generate_visualizations(
                        df=df,
                        chart_types=[chart_type] if chart_type else None,
                        query=query
                    )
                )
                
        # Create insight task for insight/analysis intent
        if (intent_type in ["INSIGHT", "ANALYSIS"] and 
            intent_confidence > self._config["insight_confidence_threshold"] and
            include_insights):
            
            # Notify insight analysis
            yield_status("Analyzing insights from data...", 25)
            
            # Prepare parameters
            columns_to_use = intent.columns if hasattr(intent, 'columns') else None
            
            # Create task
            analysis_tasks["insight_started"] = True
            
            if hasattr(self.chat_service, "generate_insights"):
                analysis_tasks["insights"] = asyncio.create_task(
                    self.chat_service.generate_insights(
                        file_id=file_id,
                        file_path=file_path,
                        content="",
                        query=query,
                        columns=columns_to_use
                    )
                )
            elif self.analyze_service:
                # Fallback: use analyze_service directly
                analysis_tasks["insights"] = asyncio.create_task(
                    self.analyze_service.generate_insights(
                        df=df,
                        insight_types=None,
                        query=query
                    )
                )
    
    def _setup_additional_analysis_tasks(
        self,
        analysis_tasks: Dict[str, Any],
        file_id: Optional[str],
        file_path: Optional[str],
        df: Optional[pd.DataFrame],
        content: str,
        query: str,
        include_visualizations: bool,
        include_insights: bool
    ) -> None:
        """
        Set up additional tasks if not initialized earlier by intent
        
        Args:
            analysis_tasks: Dict to store tasks
            file_id: File ID
            file_path: File path
            df: DataFrame
            content: Response content so far
            query: User query
            include_visualizations: Whether to include visualizations
            include_insights: Whether to include insights
        """
        # Can't initialize tasks without df or file information
        if not (file_id and file_path and df is not None):
            return
            
        # Handle visualization if not started yet
        if "visualization_started" not in analysis_tasks and include_visualizations and self._config["auto_generate_viz"]:
            # Check if content indicates visualization
            viz_keywords = ["visualize", "plot", "chart", "graph", "show me", "display"]
            if any(keyword in content.lower() for keyword in viz_keywords):
                # Create task
                analysis_tasks["visualization_started"] = True
                
                if hasattr(self.chat_service, "generate_visualizations"):
                    analysis_tasks["visualizations"] = asyncio.create_task(
                        self.chat_service.generate_visualizations(
                            file_id=file_id,
                            file_path=file_path,
                            content=content,
                            query=query
                        )
                    )
                elif self.analyze_service:
                    # Fallback: use analyze_service directly
                    analysis_tasks["visualizations"] = asyncio.create_task(
                        self.analyze_service.generate_visualizations(
                            df=df,
                            chart_types=None,
                            query=query
                        )
                    )
        
        # Similarly for insights
        if "insight_started" not in analysis_tasks and include_insights and self._config["auto_generate_viz"]:
            # Check if content indicates insights
            insight_keywords = ["insight", "analyze", "pattern", "find", "discover", "trends"]
            if any(keyword in content.lower() for keyword in insight_keywords):
                # Create task
                analysis_tasks["insight_started"] = True
                
                if hasattr(self.chat_service, "generate_insights"):
                    analysis_tasks["insights"] = asyncio.create_task(
                        self.chat_service.generate_insights(
                            file_id=file_id,
                            file_path=file_path,
                            content=content,
                            query=query
                        )
                    )
                elif self.analyze_service:
                    # Fallback: use analyze_service directly
                    analysis_tasks["insights"] = asyncio.create_task(
                        self.analyze_service.generate_insights(
                            df=df,
                            insight_types=None,
                            query=query
                        )
                    )
    
    async def _process_analysis_results(
        self,
        analysis_tasks: Dict[str, Any],
        chat_id: Optional[str],
        message_id: Optional[str]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process results from analysis tasks and send to client
        
        Args:
            analysis_tasks: Dict with tasks
            chat_id: Chat ID
            message_id: Message ID
            
        Returns:
            Tuple[Optional[List[VisualizationData]], Optional[List[InsightData]]]:
                - Visualizations (if any)
                - Insights (if any)
        """
        viz_data = None
        insight_data = None
        
        # Process visualizations
        if "visualizations" in analysis_tasks:
            try:
                visualizations = await analysis_tasks["visualizations"]
                if visualizations:
                    # Convert models to dicts for serialization
                    viz_dicts = self._convert_model_to_dict(visualizations)
                    
                    yield {
                        "event": "chat-visualizations",
                        "data": json.dumps({
                            "visualizations": viz_dicts,
                            "chat_id": chat_id,
                            "message_id": message_id
                        })
                    }
                    
                    viz_data = visualizations
            except Exception as e:
                logger.error(f"Error processing visualizations: {str(e)}", exc_info=True)
        
        # Process insights
        if "insights" in analysis_tasks:
            try:
                insights = await analysis_tasks["insights"]
                if insights:
                    # Convert models to dicts for serialization
                    insight_dicts = self._convert_model_to_dict(insights)
                    
                    yield {
                        "event": "chat-insights",
                        "data": json.dumps({
                            "insights": insight_dicts,
                            "chat_id": chat_id,
                            "message_id": message_id
                        })
                    }
                    
                    insight_data = insights
            except Exception as e:
                logger.error(f"Error processing insights: {str(e)}", exc_info=True)
        
        yield {
            "event": "analysis-complete",
            "data": json.dumps({
                "visualizations": self._convert_model_to_dict(viz_data) if viz_data else None,
                "insights": self._convert_model_to_dict(insight_data) if insight_data else None,
                "chat_id": chat_id,
                "message_id": message_id
            })
        }
    
    def _convert_model_to_dict(self, models: List[Any]) -> List[Dict[str, Any]]:
        """
        Convert models to dicts for serialization
        
        Args:
            models: List of model objects
            
        Returns:
            List[Dict[str, Any]]: List of dicts
        """
        result = []
        
        for model in models:
            if hasattr(model, "model_dump"):
                # Pydantic v2
                result.append(model.model_dump())
            elif hasattr(model, "dict"):
                # Pydantic v1
                result.append(model.dict())
            elif isinstance(model, dict):
                # Already a dict
                result.append(model)
            else:
                # Convert to dict using __dict__
                result.append(vars(model))
        
        return result
    
    async def stream_analysis_progress(
        self,
        file_id: str,
        file_path: str,
        analysis_type: str = "full"
    ) -> EventSourceResponse:
        """
        Stream progress of complex data analysis
        
        Args:
            file_id: File ID
            file_path: File path
            analysis_type: Analysis type
            
        Returns:
            EventSourceResponse: Server-Sent Events response
        """
        async def progress_generator() -> AsyncGenerator[Dict[str, Any], None]:
            error_occurred = False
            last_heartbeat = time.time()
            
            try:
                # Initialize analyze_service if not present
                if not self.analyze_service:
                    self.analyze_service = AnalyzeService(file_id, file_path)
                
                # Send start message
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "file_id": file_id,
                        "progress": 0,
                        "status": "starting",
                        "message": "Starting analysis..."
                    })
                }
                
                # Step 1: Load and validate file
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "file_id": file_id,
                        "progress": 10,
                        "status": "loading",
                        "message": "Loading and validating file..."
                    })
                }
                
                # Load file with ValidationService
                df = None
                quality_report = None
                
                try:
                    if self.validation_service:
                        df, quality_report = await self.validation_service.load_and_validate_data(
                            file_path, sample=False, max_rows=None
                        )
                    
                    # Heartbeat check
                    current_time = time.time()
                    if current_time - last_heartbeat > self._heartbeat_interval:
                        yield {
                            "event": "heartbeat",
                            "data": json.dumps({
                                "timestamp": str(current_time)
                            })
                        }
                        last_heartbeat = current_time
                    
                    # Send file information
                    file_info = {}
                    
                    if df is not None and hasattr(df, 'shape'):
                        file_info = {
                            "rows": df.shape[0],
                            "columns": df.shape[1],
                            "column_names": df.columns.tolist()
                        }
                        
                        # Add quality info if present
                        if quality_report:
                            file_info["quality"] = quality_report
                        
                        # Report validation complete
                        yield {
                            "event": "progress",
                            "data": json.dumps({
                                "file_id": file_id,
                                "progress": 30,
                                "status": "validated",
                                "message": "File validated successfully",
                                "file_info": file_info
                            })
                        }
                    else:
                        raise ValueError("Unable to load file or file is empty")
                        
                except Exception as e:
                    error_occurred = True
                    logger.error(f"Error loading file: {str(e)}", exc_info=True)
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "file_id": file_id,
                            "error": f"Error loading file: {str(e)}"
                        })
                    }
                    return
                
                # Begin analysis in background
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "file_id": file_id,
                        "progress": 40,
                        "status": "analyzing",
                        "message": "Starting data analysis..."
                    })
                }
                
                # Run analysis by type
                try:
                    # Create different analysis content based on analysis_type
                    analysis_task = None
                    
                    if analysis_type == "full":
                        analysis_task = asyncio.create_task(
                            self.analyze_service.run_analysis(df)
                        )
                    elif analysis_type == "quality":
                        analysis_task = asyncio.create_task(
                            self.analyze_service.run_analysis(df, "quality")
                        )
                    elif analysis_type == "statistics":
                        analysis_task = asyncio.create_task(
                            self.analyze_service.run_analysis(df, "statistics")
                        )
                    elif analysis_type == "visualization":
                        analysis_task = asyncio.create_task(
                            self.analyze_service.generate_visualizations(df)
                        )
                    elif analysis_type == "insights":
                        analysis_task = asyncio.create_task(
                            self.analyze_service.run_analysis(df, "insights")
                        )
                    else:
                        # Fallback: full analysis
                        analysis_task = asyncio.create_task(
                            self.analyze_service.run_analysis(df)
                        )
                    
                    # Report analysis in progress
                    yield {
                        "event": "progress",
                        "data": json.dumps({
                            "file_id": file_id,
                            "progress": 50,
                            "status": "analyzing",
                            "message": "Analyzing data structure..."
                        })
                    }
                    
                    # Update progress
                    progress_values = [50, 60, 70, 80, 90]
                    progress_messages = [
                        "Analyzing data structure...",
                        "Finding insights...",
                        "Analyzing correlations...",
                        "Discovering patterns...",
                        "Finalizing results..."
                    ]
                    
                    for i, progress in enumerate(progress_values):
                        await asyncio.sleep(1.0)
                        
                        # Heartbeat check
                        current_time = time.time()
                        if current_time - last_heartbeat > self._heartbeat_interval:
                            yield {
                                "event": "heartbeat",
                                "data": json.dumps({
                                    "timestamp": str(current_time)
                                })
                            }
                            last_heartbeat = current_time
                        
                        # Update progress
                        yield {
                            "event": "progress",
                            "data": json.dumps({
                                "file_id": file_id,
                                "progress": progress,
                                "status": "analyzing",
                                "message": progress_messages[i]
                            })
                        }
                    
                    # Wait for analysis result
                    analysis_result = await analysis_task
                    
                    # Heartbeat check
                    current_time = time.time()
                    if current_time - last_heartbeat > self._heartbeat_interval:
                        yield {
                            "event": "heartbeat",
                            "data": json.dumps({
                                "timestamp": str(current_time)
                            })
                        }
                        last_heartbeat = current_time
                    
                    # Report completion
                    yield {
                        "event": "progress",
                        "data": json.dumps({
                            "file_id": file_id,
                            "progress": 100,
                            "status": "completed",
                            "message": "Analysis completed"
                        })
                    }
                    
                    # Send full result - convert to dict if needed
                    result_dict = None
                    if isinstance(analysis_result, dict):
                        result_dict = analysis_result
                    else:
                        result_dict = self._convert_model_to_dict([analysis_result])[0]
                        
                    # Convert NumPy types if needed
                    if hasattr(self.analyze_service, "_convert_numpy_types"):
                        result_dict = self.analyze_service._convert_numpy_types(result_dict)
                    
                    yield {
                        "event": "result",
                        "data": json.dumps({
                            "file_id": file_id,
                            "analysis": result_dict
                        })
                    }
                except Exception as e:
                    error_occurred = True
                    logger.error(f"Error in analysis: {str(e)}", exc_info=True)
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "file_id": file_id,
                            "error": f"Error during analysis: {str(e)}"
                        })
                    }
                
                # Final heartbeat
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({
                        "timestamp": str(time.time())
                    })
                }
                
            except Exception as e:
                error_occurred = True
                logger.error(f"Error in analysis streaming: {str(e)}", exc_info=True)
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "file_id": file_id,
                        "error": str(e)
                    })
                }
            finally:
                # Always send complete event
                if error_occurred:
                    yield {
                        "event": "complete",
                        "data": json.dumps({
                            "file_id": file_id,
                            "message": "Processing interrupted due to error"
                        })
                    }
                else:
                    yield {
                        "event": "complete",
                        "data": json.dumps({
                            "file_id": file_id,
                            "message": "Analysis completed successfully"
                        })
                    }
                
        return EventSourceResponse(progress_generator())