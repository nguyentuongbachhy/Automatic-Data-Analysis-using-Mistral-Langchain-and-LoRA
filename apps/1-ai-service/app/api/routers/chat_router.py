import json
import logging
import time
import os
from typing import Optional
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain.memory import ConversationBufferMemory

from fastapi import APIRouter, Depends, Path, Query, Body
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import (
    ValidationServiceDep, ModelServiceDep, IntentServiceDep, CacheDep,
    get_performance_monitor, timed_endpoint, get_chat_service, get_analyze_service
)
from app.models.chat import ChatRequest, IntentType
from app.models.common import ApiResponse, ResponseStatus
from app.services.streaming.streaming_manager import StreamingManager
from app.services.chat.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/get-chats", response_model=ApiResponse)
async def get_chats(
    user_id: str = Query(..., description="User ID to retrieve chats for"),
    file_id: Optional[str] = Query(None, description="Optional file ID to filter chats"),
    limit: int = Query(20, description="Pagination limit"),
    offset: int = Query(0, description="Pagination offset"),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Get chats for a user, optionally filtered by file ID"""
    try:
        # Chuẩn bị conditions cho select
        conditions = {
            "userId": user_id,
            "isArchived": False
        }
        
        # Thêm điều kiện lọc theo file_id nếu có
        if file_id:
            conditions["fileId"] = file_id
        
        # Sử dụng phương thức get_chats mới
        chats = chat_service.get_chats(
            user_id=user_id, 
            order_by="updatedAt DESC", 
            limit=limit, 
            offset=offset
        )
        
        if chats is None:  # Xử lý trường hợp lỗi trả về None
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Failed to retrieve chats"
            )
        
        total_count = chat_service.count_chats(user_id=user_id, file_id=file_id)
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={
                "chats": chats,
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving chats: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )

@router.post("/create", response_model=ApiResponse)
@timed_endpoint
async def create_chat(
    request: dict = Body(...),
    chat_service: ChatService = Depends(get_chat_service),
    model_service: ModelServiceDep = None,
):
    """Tạo chat mới không yêu cầu query"""
    try:
        file_id = request.get("file_id")
        title = request.get("title", "New Chat")
        user_id = request.get("user_id")
        
        if not user_id:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="user_id is required"
            )
        
        # Tạo chat ID mới
        chat_id = chat_service.create_chat(file_id, user_id, title)

        if not chat_id:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Failed to create chat"
            )
        
        # Nếu sử dụng LangChain, khởi tạo memory cho chat này
        if model_service and hasattr(model_service, "_langchain_memory"):
            chat_history = InMemoryChatMessageHistory()
            memory = ConversationBufferMemory(
                memory_key='chat_history', 
                return_messages=True,
                chat_memory=chat_history
            )
            model_service._langchain_memory[chat_id] = memory
            
            # Thêm system message nếu có file
            if file_id:
                system_message = f"This is a chat about file {file_id}. Help the user analyze the data."
                memory.chat_memory.add_message({"role": "system", "content": system_message})
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={
                "chat_id": chat_id,
                "title": title,
                "file_id": file_id,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "user_id": user_id
            }
        )
    except Exception as e:
        logger.error(f"Error creating chat: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )
    
@router.put("/archive/{chat_id}", response_model=ApiResponse)
async def archive_chat(
    chat_id: str = Path(..., description="Chat ID to archive"),
    chat_service: ChatService = Depends(get_chat_service),
) -> ApiResponse:
    """Archive a chat (mark as archived without deleting)"""
    try:
        # Cần thêm phương thức archive_chat trong ChatService
        success = chat_service.archive_chat(chat_id)
        
        if not success:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error=f"Failed to archive chat {chat_id}"
            )
            
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={"archived": True, "chat_id": chat_id}
        )
    except Exception as e:
        logger.error(f"Error archiving chat: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )

@router.get("/messages/{chat_id}", response_model=ApiResponse)
async def get_chat_messages(
    chat_id: str = Path(..., description="Chat ID to retrieve messages for"),
    limit: int = Query(50, description="Pagination limit"),
    offset: int = Query(0, description="Pagination offset"),
    load_to_memory: bool = Query(True, description="Load messages into LangChain memory"),
    chat_service: ChatService = Depends(get_chat_service),
    model_service: ModelServiceDep = None
) -> ApiResponse:
    """Get messages for a chat and optionally load them into LangChain memory"""
    try:
        # Cập nhật phương thức để hỗ trợ limit và offset
        messages = chat_service.get_messages(
            chat_id=chat_id, 
            order_by="createdAt ASC",
            limit=limit,
            offset=offset
        )
        
        if messages is None:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error=f"Failed to retrieve messages for chat {chat_id}"
            )
        
        # Tải vào memory nếu cần
        memory_loaded = False
        if load_to_memory and model_service:
            memory_loaded = chat_service.load_chat_history_to_memory(chat_id)
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={
                "messages": messages,
                "chat_id": chat_id,
                "total": len(messages),
                "memory_loaded": memory_loaded
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving chat messages: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )

@router.post("/message", response_model=ApiResponse)
@timed_endpoint
async def process_message(
    request: ChatRequest,
    cache: CacheDep,
    chat_service: ChatService = Depends(get_chat_service),
    monitor = Depends(get_performance_monitor),
) -> ApiResponse:
    """Process chat message with one-shot, no LangChain approach"""
    try:
        start_time = time.time()
        
        # Xác thực yêu cầu
        if not request.chat_id:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Chat ID is required"
            )
        
        file_path = chat_service.get_file_path(request.file_id, request.user_id)

        # Tạo cache key nếu cần
        cached_response = cache.get(request.chat_id) if request.use_cache else None
        
        if cached_response:
            logger.info("Using cached chat response")
            proc_time = time.time() - start_time
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                data=cached_response,
                meta={"processing_time": proc_time, "cached": True}
            )
        
        # Lưu tin nhắn của người dùng vào database
        user_message_id = chat_service.insert_message(
            chat_id=request.chat_id,
            role="USER",
            content=request.query
        )
        
        if not user_message_id:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Failed to save user message"
            )
        
        # Chuẩn bị prompt và context
        system_prompt, intent, df = await chat_service.prepare_prompt(
            query=request.query,
            file_id=request.file_id,
            file_path=file_path,
        )
        
        # Generate response sử dụng Mistral
        full_prompt = system_prompt + "\n\nUser: " + request.query + "\n\nAssistant: "
        
        if hasattr(chat_service.model_service, 'mistral') and hasattr(chat_service.model_service.mistral, 'generate'):
            response_text = chat_service.model_service.mistral.generate(
                prompt=full_prompt,
                conversation_id=request.chat_id,
                use_history=False
            )
        else:
            raise ValueError("Mistral generate method không khả dụng")
        
        # Tạo visualizations và insights nếu cần
        visualizations = None
        insights = None
        
        if request.file_id and file_path and df is not None:
            # Tạo AnalyzeService
            analyze_service = chat_service._create_analyze_service(request.file_id, request.user_id)
            
            # Xác định nếu cần tạo visualizations dựa trên query và intent
            if "visualize" in request.query.lower() or "chart" in request.query.lower() or (intent and intent.intent in [IntentType.VISUALIZATION, IntentType.ANALYSIS]):
                visualizations = await analyze_service.generate_visualizations(df, None, request.query)
            
            # Tương tự với insights
            if "insight" in request.query.lower() or "analyze" in request.query.lower() or (intent and intent.intent in [IntentType.INSIGHT, IntentType.ANALYSIS]):
                insights = await analyze_service.generate_insights(df, None, request.query)
        
        # Tạo metadata nếu có visualizations hoặc insights
        metadata = {}
        if visualizations or insights:
            metadata = {
                "has_visualizations": visualizations is not None,
                "has_insights": insights is not None
            }
        
        # Lưu tin nhắn của hệ thống vào database
        assistant_message_id = chat_service.insert_message(
            chat_id=request.chat_id,
            role="ASSISTANT",
            content=response_text,
            metadata=metadata
        )
        
        if not assistant_message_id:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Failed to save assistant message"
            )
        
        # Cập nhật lastMessage trong bảng Chat
        chat_service.update_last_message(request.chat_id, assistant_message_id)
        
        # Tạo response object
        response_obj = {
            "id": assistant_message_id,
            "user_message_id": user_message_id,
            "response": response_text,
            "chat_id": request.chat_id,
            "used_langchain": False,
            "one_shot": True
        }
        
        # Thêm visualizations và insights nếu có
        if visualizations:
            response_obj["visualizations"] = [
                viz.model_dump() if hasattr(viz, "model_dump") else viz.dict() if hasattr(viz, "dict") else viz
                for viz in visualizations
            ]
        
        if insights:
            response_obj["insights"] = [
                insight.model_dump() if hasattr(insight, "model_dump") else insight.dict() if hasattr(insight, "dict") else insight
                for insight in insights
            ]
        
        # Chuyển đổi NumPy types
        response_obj = chat_service._convert_numpy_types(response_obj)
        
        # Cache nếu cần
        if request.use_cache:
            cache.set(request.chat_id, response_obj)
        
        # Ghi nhận thời gian xử lý
        proc_time = time.time() - start_time
        logger.info(f"Message processed in {proc_time:.2f}s")
        monitor.record_chat_processing(proc_time)
        
        # Trả về kết quả
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data=response_obj,
            meta={"processing_time": proc_time}
        )
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        monitor.record_error("chat_message", str(e))
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )
    
@router.get("/stream", response_class=EventSourceResponse)
async def chat_stream(
    model_service: ModelServiceDep,
    intent_service: IntentServiceDep,
    validation_service: ValidationServiceDep,
    query: str = Query(..., description="User query"),
    user_id: str = Query(..., description="User ID"),
    chat_id: str = Query(..., description="Chat ID"),
    message_id: str = Query(..., description="Message ID"),
    file_id: Optional[str] = Query(None, description="File ID"),
    chat_service: ChatService = Depends(get_chat_service),
    include_visualizations: bool = Query(True, description="Include visualizations in response"),
    include_insights: bool = Query(True, description="Include insights in response"),
    show_thinking: bool = Query(True, description="Show Chain-of-Thought reasoning"),
):
    """Stream chat response và lưu tin nhắn vào database"""
    try:
        # Đảm bảo có chat_id
        if not chat_id:
            raise ValueError("Chat ID is required")
        
        file_path = chat_service.get_file_path(file_id, user_id)
        analyze_service = get_analyze_service(file_id, user_id, model_service)

        streaming_manager = StreamingManager(model_service, chat_service, analyze_service, intent_service, validation_service)

        message_id = chat_service.insert_message(
            chat_id=chat_id,
            role="USER",
            content=query,
            metadata={"userId": user_id}
        )

        if not message_id:
            raise ValueError("Failed to insert user message into database")
    
        if not hasattr(streaming_manager.model_service, 'run_langchain_agent') or not hasattr(streaming_manager.model_service, 'stream_langchain_reasoning'):
            raise ValueError("LangChain không được cấu hình đúng. Endpoint này bắt buộc phải dùng LangChain.")
        
        if streaming_manager._config:
            streaming_manager._config["show_thinking"] = show_thinking
            streaming_manager._config["use_langchain"] = True  # Đảm bảo bật LangChain
        
        # Return event source response
        return await streaming_manager.stream_chat_response(
            file_id=file_id,
            file_path=file_path,
            query=query,
            chat_id=chat_id,
            message_id=message_id,
            include_visualizations=include_visualizations,
            include_insights=include_insights,
        )
    except Exception as e:
        logger.error(f"Error setting up chat stream: {str(e)}", exc_info=True)
        # Create manual streaming response with error
        async def error_stream(error):
            yield {
                "event": "error",
                "data": json.dumps({"error": str(error)})
            }
        return EventSourceResponse(error_stream(e))

@router.post("/semantic-search", response_model=ApiResponse)
@timed_endpoint
async def semantic_search(
    request: ChatRequest,
    validation_service: ValidationServiceDep,
    model_service: ModelServiceDep,
    chat_service: ChatService = Depends(get_chat_service),
    top_k: int = Query(5, description="Number of results to return"),
) -> ApiResponse:
    """Semantic search in data using embedded model"""
    try:
        file_path = chat_service.get_file_path(request.file_id, request.user_id)

        if not file_path:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="file_path is required for semantic search"
            )
        
        file_path = chat_service.get_file_path(request.file_id, request.user_id)

        # Validate file existence
        if not os.path.exists(file_path):
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error=f"File not found: {file_path}"
            )
        
        # Use semantic_search from chat_service if available
        if hasattr(chat_service, "semantic_search_in_file"):
            results = await chat_service.semantic_search_in_file(
                query=request.query,
                file_id=request.file_id,
                file_path=file_path,
                top_k=top_k
            )
        # Otherwise use model_service directly
        elif hasattr(model_service, "semantic_search"):
            # Load file
            df = await validation_service.validate_and_load_file(file_path, sample_rows=10000)
            
            # Convert rows to documents
            documents = []
            for _, row in df.iterrows():
                doc = ", ".join([f"{col}: {row[col]}" for col in df.columns])
                documents.append(doc)
            
            # Limit documents
            max_docs = 1000
            if len(documents) > max_docs:
                documents = documents[:max_docs]
            
            # Perform search
            search_results = await model_service.semantic_search(
                request.query, documents, top_k
            )
            
            # Format results
            results = []
            for res in search_results:
                doc_index = res.get("index", 0)
                if 0 <= doc_index < len(df):
                    row_data = df.iloc[doc_index].to_dict()
                    results.append({
                        "row_index": doc_index,
                        "score": res.get("score", 0),
                        "data": row_data
                    })
        else:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Semantic search not supported by current services"
            )

        # Convert NumPy types to Python native types
        if hasattr(chat_service, "_convert_numpy_types"):
            results = chat_service._convert_numpy_types(results)
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={"results": results}
        )
    except Exception as e:
        logger.error(f"Error in semantic search: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )

@router.post("/intent-detect", response_model=ApiResponse)
@timed_endpoint
async def detect_intent(
    request: ChatRequest,
    validation_service: ValidationServiceDep,
    intent_service: IntentServiceDep,
    chat_service: ChatService = Depends(get_chat_service)
) -> ApiResponse:
    """Detect user intent from query using ML model"""
    try:
        file_path = chat_service.get_file_path(request.file_id, request.user_id)
        if not file_path:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="file_path is required for intent detection"
            )
        
        # Validate file existence
        if not os.path.exists(file_path):
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error=f"File not found: {file_path}"
            )
        
        # Read file for intent detection
        df = await validation_service.validate_and_load_file(
            file_path, sample_rows=10000
        )
        
        intent = await intent_service.detect_intent(request.query, df)
        
        # Prepare data
        intent_data = {
            "intent": intent.intent.value if hasattr(intent.intent, 'value') else str(intent.intent),
            "confidence": float(intent.confidence) if hasattr(intent, 'confidence') else 0.0,
            "columns": intent.columns if hasattr(intent, 'columns') else [],
            "visualization_type": intent.visualization_type if hasattr(intent, 'visualization_type') else None,
            "parameters": intent.parameters if hasattr(intent, 'parameters') else {}
        }
        
        # Convert NumPy types to Python native types if BaseService exists
        if hasattr(intent_service, "_convert_numpy_types"):
            intent_data = intent_service._convert_numpy_types(intent_data)

        # Return result
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data=intent_data
        )
    except Exception as e:
        logger.error(f"Error detecting intent: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )


@router.get("/history/{user_id}", response_model=ApiResponse)
async def get_chat_history(
    model_service: ModelServiceDep,
    user_id: str = Path(..., description="User ID to retrieve history for"),
    chat_service: ChatService = Depends(get_chat_service),
) -> ApiResponse:
    """Get chat history from user ID"""
    try:
        # For LangChain integration, get from memory
        history = []
        conversation_id = None
        
        # Get conversation ID from chat service
        if hasattr(chat_service, "_conversation_map"):
            conversation_id = chat_service._conversation_map.get(user_id)
        
        # If using LangChain, get from memory
        if conversation_id and hasattr(model_service, "_langchain_memory") and conversation_id in model_service._langchain_memory:
            memory = model_service._langchain_memory[conversation_id]
            # Get messages from memory
            if hasattr(memory, "chat_memory") and hasattr(memory.chat_memory, "messages"):
                history = []
                for msg in memory.chat_memory.messages:
                    if hasattr(msg, "type") and hasattr(msg, "content"):
                        history.append({
                            "role": msg.type,
                            "content": msg.content
                        })
        else:
            # Legacy approach
            if conversation_id and hasattr(model_service, "_get_conversation_history"):
                history = model_service._get_conversation_history(conversation_id)
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={"messages": history}
        )
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )


@router.delete("/history/{user_id}", response_model=ApiResponse)
async def clear_chat_history(
    user_id: str = Path(..., description="User ID to clear history for"),
    model_service: ModelServiceDep = None,
    chat_service: ChatService = Depends(get_chat_service),
) -> ApiResponse:
    """Clear chat history for user ID"""
    try:
        # Clear in chat service
        result = await chat_service.clear_user_conversation(user_id)
        
        # Get conversation ID
        conversation_id = None
        if hasattr(chat_service, "_conversation_map"):
            conversation_id = chat_service._conversation_map.get(user_id)
            
        # Also clear in model service if using LangChain
        if conversation_id and model_service and hasattr(model_service, "_langchain_memory"):
            if conversation_id in model_service._langchain_memory:
                del model_service._langchain_memory[conversation_id]
            
            if hasattr(model_service, "_langchain_agents") and conversation_id in model_service._langchain_agents:
                del model_service._langchain_agents[conversation_id]
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={"cleared": result}
        )
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )
    
@router.post("/sql-query", response_model=ApiResponse)
@timed_endpoint
async def execute_sql_query(
    query: str = Query(..., description="SQL query to execute"),
    model_service: ModelServiceDep = None,
) -> ApiResponse:
    """Execute SQL query directly on PostgreSQL database"""
    try:
        if not model_service:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Model service not available"
            )
        
        # Check if _execute_sql exists
        if not hasattr(model_service, "_execute_sql"):
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="SQL execution not available in model service"
            )
        
        # Execute query
        result = model_service._execute_sql(query)
        
        # Determine if result is an error
        if isinstance(result, str) and result.startswith("Error:"):
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error=result
            )
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={"result": result}
        )
    except Exception as e:
        logger.error(f"Error executing SQL query: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )


@router.get("/db-schema", response_model=ApiResponse)
async def get_database_schema(
    model_service: ModelServiceDep = None,
) -> ApiResponse:
    """Get PostgreSQL database schema information"""
    try:
        if not model_service:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Model service not available"
            )
        
        # Check if _describe_database exists
        if not hasattr(model_service, "_describe_database"):
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Database schema information not available in model service"
            )
        
        # Get schema information
        schema_info = model_service._describe_database()
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={"schema": schema_info}
        )
    except Exception as e:
        logger.error(f"Error getting database schema: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )

@router.post("/stream-analysis/{file_id}", response_class=EventSourceResponse)
async def stream_analysis(
    model_service: ModelServiceDep,
    intent_service: IntentServiceDep,
    validation_service: ValidationServiceDep,
    chat_service: ChatService = Depends(get_chat_service),
    file_id: str = Path(..., description="File ID to analyze"),
    user_id: str = Path(..., description="User ID to analyze"),
    analysis_type: str = Query("full", description="Type of analysis to perform"),
):
    """Stream progress of complex data analysis"""
    try:
        file_path = chat_service.get_file_path(file_id, user_id)
        # Validate file existence
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        analyze_service = get_analyze_service(file_id, user_id, model_service)
        streaming_manager = StreamingManager(model_service, chat_service, analyze_service, intent_service, validation_service)

        # Stream analysis progress
        return await streaming_manager.stream_analysis_progress(
            file_id=file_id,
            file_path=file_path,
            analysis_type=analysis_type
        )
    except Exception as e:
        logger.error(f"Error setting up analysis stream: {str(e)}", exc_info=True)
        # Create manual streaming response with error
        async def error_stream():
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
        return EventSourceResponse(error_stream())


@router.get("/health", response_model=ApiResponse)
async def chat_health_check(
    model_service: ModelServiceDep,
    chat_service: ChatService = Depends(get_chat_service),
) -> ApiResponse:
    """Check health of chat service and ML components with LangChain status"""
    try:
        # Check health from chat service
        chat_health = await chat_service.health_check()
        
        # Check model service
        model_health = model_service.get_system_info()
        
        # Get LangChain info
        langchain_info = {}
        if hasattr(model_service, "_langchain_model"):
            langchain_info["enabled"] = model_service._langchain_model is not None
        if hasattr(model_service, "_langchain_memory"):
            langchain_info["active_conversations"] = len(model_service._langchain_memory)
        if hasattr(model_service, "_function_registry"):
            langchain_info["registered_functions"] = len(model_service._function_registry)
            langchain_info["function_names"] = list(model_service._function_registry.keys())
        
        # Ensure no NumPy types
        if hasattr(chat_service, "_convert_numpy_types"):
            chat_health = chat_service._convert_numpy_types(chat_health)
            model_health = chat_service._convert_numpy_types(model_health)
            langchain_info = chat_service._convert_numpy_types(langchain_info)
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={
                "chat_service": chat_health,
                "model_service": model_health,
                "langchain": langchain_info,
                "status": "healthy"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e),
            data={"status": "unhealthy"}
        )