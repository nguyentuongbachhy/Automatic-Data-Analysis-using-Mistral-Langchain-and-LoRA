# app/services/chat/chat_service.py
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union, AsyncGenerator
from uuid import uuid4 as v4
from datetime import datetime
import time
import os
import textwrap
import re

import numpy as np
import pandas as pd

from app.core.cache import InferenceCache
from app.models.analysis import (
    VisualizationData, InsightData, ChartType
)
from app.models.chat import IntentType, UserIntent

from app.services.base_service import BaseService
from app.services.model_service import ModelService
from app.services.intent_service import IntentDetectionService
from app.services.validation_service import ValidationService
from app.services.analyze_service import AnalyzeService

# Import LangChain components for integration
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain.memory import ConversationBufferMemory

# Import from ml module
from ml.tools.postgres_connector import PostgreSQLConnector

logger = logging.getLogger(__name__)

class ChatService(BaseService):
    """
    Enhanced chat service with LangChain integration and tool support
    """

    def __init__(
        self,
        model_service: Optional[ModelService] = None,
        intent_service: Optional[IntentDetectionService] = None,
        validation_service: Optional[ValidationService] = None,
        config: Optional[Union[Dict, Any]] = None,
        cache: Optional[InferenceCache] = None
    ):
        """Initialize service with full integration"""
        super().__init__(config=config)
        
        # Main services
        self.model_service = model_service or ModelService.get_instance()
        self.intent_service = intent_service
        self.validation_service = validation_service
        self.connect = PostgreSQLConnector()

        # Cache for messages and file contexts
        self.cache = cache or InferenceCache()
        self.message_context_cache = {}
        self.file_context_cache = {}
        
        # Track conversation IDs
        self._conversation_map = {}  # map user_id -> conversation_id
        
        # Default configuration
        self._config = {
            'max_cache_items': 100,
            'sample_rows': 50,
            'enable_automatic_viz': True,
            'heartbeat_interval': 15,
            'max_history_messages': 10,
            'viz_confidence_threshold': 0.6,
            'enable_cot_prompting': True,
            'use_langchain_agent': True,
            'show_thinking_process': True
        }
        
        # If BaseService has config, update
        if hasattr(self, 'config') and isinstance(self.config, dict):
            chat_config = self.config.get('chat_service', {})
            self._config.update(chat_config)
        
        logger.info("ChatService initialized with LangChain integration")
    
    def create_chat(self, file_id: str, user_id: str, title: str) -> Optional[str]:
        """
        Create chat and insert it into database
        
        Args:
            file_id: ID of the associated file (can be None)
            user_id: ID of the user creating the chat
            title: Title of the chat
        
        Returns:
            Chat ID if successfully created, None otherwise
        """
        try:
            chat_id = str(v4())
            current_time = datetime.now().isoformat()
            
            success = self.connect.insert('Chat', {
                'id': chat_id,
                'userId': user_id,
                'fileId': file_id,
                'title': title,
                'createdAt': current_time,
                'updatedAt': current_time,
                'isArchived': False,
                'lastMessage': None
            })
            if success:
                return chat_id
            return None
        except Exception as e:
            logger.error(f"Error creating chat: {str(e)}", exc_info=e)
            return None
    
    def get_file_path(self,file_id: str, user_id: str) -> str:
        """
        Get path with file_id and user_id

        Args:
            file_id: ID of file
            user_id: ID of user
        """
        try:
            results = self.connect.select('File',columns={"path"}, conditions={
                "id": file_id,
                "userId": user_id
            })

            if results and isinstance(results, list):
                return results[0]["path"]
            return None
        except Exception as e:
            logger.error(f"Error getting path with file_id={file_id} user_id={user_id}: {str(e)}", exc_info=e)
            return None

    def get_chats(self, user_id:str, order_by:str="updatedAt DESC", limit:int=20, offset:int=0) -> List[Dict[str, Any]]:
        """
        Get all chats of user with user_id

        Args:
            user_id: ID of user
            order_by: Sorting string default "updatedAt DESC"
            limit: Maximum number of records to return
            offset: Starting position for data retrieval
        Returns:
            List[Dict[str, Any]]: Query result as a list of dictionaries
        """

        try:
            chats = self.connect.select('Chat', conditions={
                "userId": user_id,
                "isArchived": False
            }, order_by=order_by, limit=limit, offset=offset)
            
            return chats
        except Exception as e:
            logger.error(f"Error getting chats with user_id={user_id}: {str(e)}", exc_info=e)
            return None

    def get_messages(self, chat_id: str, order_by:str="createdAt ASC", limit: int = None, offset: int = None) -> list[Dict[str, Any]]:
        """
        Get all messages of chat with chat_id

        Args:
            chat_id: ID of chat
            order_by: Sorting string default "createdAt ASC"
            limit: Maximum number of records to return
            offset: Starting position for data retrieval
        """
        try:
            messages = self.connect.select(
                "Message", 
                columns=["id", "role", "content", "metadata", "createdAt", "updatedAt"], 
                conditions={"chatId": chat_id}, 
                order_by=order_by,
                limit=limit,
                offset=offset
            )
            
            # Xử lý metadata từ JSON string sang dictionary
            for msg in messages:
                if 'metadata' in msg and msg['metadata']:
                    if isinstance(msg['metadata'], str):
                        try:
                            msg['metadata'] = json.loads(msg['metadata'])
                        except:
                            msg['metadata'] = {}
            
            return messages
        except Exception as e:
            logger.error(f"Error getting messages with chat_id={chat_id}: {str(e)}", exc_info=e)
            return None

    def count_chats(self, user_id:str, file_id: Optional[str]=None) -> int:
        """
        Count the number of chats for a user

        Args:
            user_id: ID of the user
            file_id: Optional ID of the file to filter by

        Returns:
            int: Number of chats
        """
        try:
            # Chuẩn bị điều kiện
            conditions = {
                "userId": user_id,
                "isArchived": False
            }
            
            if file_id:
                conditions["fileId"] = file_id
                
            # Thực hiện truy vấn đếm thông qua select với COUNT(*)
            query = """
                SELECT COUNT(*) AS total 
                FROM "Chat" 
                WHERE "userId" = %s AND "isArchived" = FALSE
            """
            params = [user_id]
            
            if file_id:
                query += ' AND "fileId" = %s'
                params.append(file_id)
                
            count_result, _ = self.connect.execute_query(query, params)
            return count_result[0]['total'] if count_result else 0
        
        except Exception as e:
            logger.error(f"Error counting chats: {str(e)}", exc_info=True)
            return 0

    def archive_chat(self, chat_id: str) -> bool:
        """
        Đánh dấu chat là đã lưu trữ (không xóa)
        
        Args:
            chat_id: ID của chat cần lưu trữ
            
        Returns:
            bool: True nếu thành công, False nếu có lỗi
        """
        try:
            current_time = datetime.now().isoformat()
            
            # Sử dụng update của PostgreSQLConnector
            success = self.connect.update('Chat', {
                'isArchived': True,
                'updatedAt': current_time
            }, {
                'id': chat_id
            })
            
            return success
        except Exception as e:
            logger.error(f"Error archiving chat: {str(e)}", exc_info=e)
            return False

    def insert_message(self, chat_id: str, role: str, content: str, metadata: Optional[Dict]=None) -> str:
        """
        Insert message into database
        
        Args:
            chat_id: ID of chat
            role (user, assistant, system)
            content: content of message
            metadata: metadata of message
                
        Returns:
            Optional[str]: ID of message that inserted into database
        """
        try:
            message_id = str(v4())
            current_time = datetime.now().isoformat()

            # Normalize role value
            normalized_role = role.upper() if isinstance(role, str) else "USER"
            
            # Validate role
            if normalized_role not in ["USER", "ASSISTANT", "SYSTEM"]:
                normalized_role = "USER"
            
            message_data = {
                'id': message_id,
                'chatId': chat_id,
                'role': normalized_role,
                'content': content,
                'createdAt': current_time,
                'updatedAt': current_time
            }

            if metadata:
                message_data["metadata"] = json.dumps(metadata)
            
            success = self.connect.insert('Message', message_data)

            if success:
                return message_id

            return None
        except Exception as e:
            logger.error(f"Error inserting message: {str(e)}", exc_info=e)
            return None
    def update_last_message(self, chat_id: str, message_id: str) -> bool:
        """
        Update lastMessage in Chat table

        Args:
            chat_id: ID of chat
            message_id: ID of message

        Returns
            bool: True if updated successfully else False
        """
        current_time = datetime.now().isoformat()
        try:
            success = self.connect.update('Chat', {
                'lastMessage': message_id,
                'updatedAt': current_time
            }, {
                'id': chat_id
            })
            return success
        except Exception as e:
            logger.error(f"Error updating lastMessage in Chat table: {str(e)}", exc_info=e)
            return False

    async def prepare_prompt(
        self, 
        query: str, 
        file_id: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> Tuple[str, Optional[UserIntent], Optional[pd.DataFrame]]:
        """
        Prepare prompt with context from file and intent analysis
        
        Args:
            query: User query
            file_id: File ID (if any)
            file_path: File path (if any)
            user_id: User ID (to store conversation history)
            
        Returns:
            Tuple[str, Optional[UserIntent], Optional[pd.DataFrame]]: 
                - Prepared prompt
                - Detected intent (if any)
                - Loaded DataFrame (if any)
        """
        
        # DataFrame and intent to be returned
        df = None
        intent = None
        
        # Create context from file if present
        file_context = ""
        if file_id and file_path:
            try:
                # Check cache first
                cache_key = f"file_context_{file_id}"
                cached_context = self.file_context_cache.get(cache_key)
                
                if cached_context:
                    file_context = cached_context
                    logger.info(f"Using cached file context for {file_id}")
                else:
                    # Use ValidationService to load and validate data
                    df, quality_report = await self.validation_service.load_and_validate_data(
                        file_path, sample=True, max_rows=self._config['sample_rows']
                    )
                    
                    # Create file context from dataframe and quality report
                    file_context = self._create_file_context(df, file_path, quality_report)
                    
                    # Store in cache
                    self.file_context_cache[cache_key] = file_context
            except Exception as e:
                logger.error(f"Error getting file context: {str(e)}", exc_info=True)
                file_context = f"File information unavailable due to error: {str(e)}"
        
        # Detect intent if file is present
        intent_info = ""
        if file_id and file_path and self.intent_service:
            try:
                # Ensure df is loaded
                if df is None and self.validation_service:
                    df, _ = await self.validation_service.load_and_validate_data(
                        file_path, sample=True, max_rows=self._config['sample_rows']
                    )
                
                # Detect intent
                intent = await self.intent_service.detect_intent(query, df)
                
                if intent and intent.intent != IntentType.UNKNOWN:
                    intent_info = f"\nUser intent: {intent.intent.value} (confidence: {intent.confidence:.2f})"
                    if intent.columns:
                        intent_info += f"\nColumns of interest: {', '.join(intent.columns)}"
                    if intent.visualization_type:
                        intent_info += f"\nVisualization type: {intent.visualization_type}"
                        
                logger.info(f"Detected intent: {intent.intent.value if intent else 'Unknown'} with confidence: {intent.confidence if intent else 0}")
            except Exception as e:
                logger.error(f"Error detecting intent: {str(e)}", exc_info=True)
        
        # Build prompt template with Chain-of-Thought components
        # Note: This is more like a system message for LangChain now
        system_prompt = textwrap.dedent(f"""\
            You are a helpful data analysis assistant that helps users analyze data and get insights.
            You have access to powerful tools that can help you analyze data, generate visualizations, 
            and provide insights.

            When analyzing data:
            1. Break down the problem into steps
            2. Consider what tools you need
            3. Execute your plan methodically
            4. Present your findings clearly

            When thinking through a complex problem, use <thinking>...</thinking> tags to show your reasoning process.

            {file_context}
            {intent_info}

            Current date: {time.strftime("%Y-%m-%d")}
        """)
        
        # Return all components
        return system_prompt, intent, df
    
    def load_chat_history_to_memory(self, chat_id: str) -> bool:
        """
        Load message history to LangChain memory

        Args:
            chat_id: ID of chat

        Returns:
            bool: True if loaded successfully else False
        """
        try:
            if not hasattr(self.model_service, '_langchain_memory'):
                logger.warning("LangChain memory is unavailable")
                return False
            
            chat_history = InMemoryChatMessageHistory()
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                chat_memory=chat_history
            )

            messages = self.get_messages(chat_id)

            system_message = None
            for msg in messages:
                if msg['role'] == 'SYSTEM':
                    system_message = msg['content']
                    break
    
            if system_message:
                memory.chat_memory.add_message({"role": "system", "content": system_message})

            for msg in messages:
                if msg['role'] == 'USER':
                    memory.chat_memory.add_message({"role": "user", "content": msg['content']})
                elif msg['role'] == 'ASSISTANT':
                    memory.chat_memory.add_message({"role": "assistant", "content": msg['content']})
            
            # Lưu vào _langchain_memory
            self.model_service._langchain_memory[chat_id] = memory
            
            logger.info(f"Loaded {len(messages)} messages into LangChain memory for chat {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error loading chat history to memory: {str(e)}", exc_info=True)
            return False

    async def _process_message_stream(
        self,
        query: str,
        file_id: Optional[str] = None,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        user_message_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process message and stream response with Chain-of-Thought reasoning
        
        Args:
            query: User query
            file_id: File ID (if any)
            file_path: File path (if any)
            user_id: User ID (for conversation history)
            messages: Message history (if provided)
            chat_id: Chat ID for database operations
            user_message_id: User message ID for reference
            
        Yields:
            str: Streamed response tokens
        """
        try:
            # Prepare prompt
            system_prompt, intent, df = await self.prepare_prompt(query, file_id, file_path, user_id)
            
            # Collect full response for database saving (if needed)
            full_response = ""
            
            # Stream response với Chain-of-Thought reasoning
            if self._config.get('use_langchain_agent', True) and hasattr(self.model_service, 'stream_langchain_reasoning'):
                # Khởi tạo memory với system prompt nếu cần
                if hasattr(self.model_service, '_langchain_memory') and chat_id in self.model_service._langchain_memory:
                    memory = self.model_service._langchain_memory[chat_id]
                    # Add system message if it's not there yet
                    if len(memory.chat_memory.messages) == 0:
                        memory.chat_memory.add_message({"role": "system", "content": system_prompt})
                else:
                    # Create new memory with system prompt
                    chat_history = InMemoryChatMessageHistory()
                    memory = ConversationBufferMemory(
                        memory_key="chat_history",
                        return_messages=True,
                        chat_memory=chat_history
                    )
                    memory.chat_memory.add_message({"role": "system", "content": system_prompt})
                    if hasattr(self.model_service, '_langchain_memory'):
                        self.model_service._langchain_memory[chat_id] = memory
                        
                # Stream response with reasoning
                async for token in self.model_service.stream_langchain_reasoning(chat_id, query):
                    # Collect non-thinking tokens for database saving
                    if not token.startswith("<thinking>") and not "</thinking>" in token:
                        full_response += token
                    
                    yield token
            else:
                # Fallback to traditional streaming with mistral.stream
                if hasattr(self.model_service, 'mistral') and hasattr(self.model_service.mistral, 'stream'):
                    # Tạo prompt đầy đủ
                    full_prompt = system_prompt + "\n\nUser: " + query + "\n\nAssistant: "
                    
                    # Stream từ mistral
                    async for token in self.model_service.mistral.stream(
                        prompt=full_prompt, 
                        conversation_id=chat_id,
                        use_history=False  # Không sử dụng KV cache
                    ):
                        full_response += token
                        yield token
                else:
                    # Không có phương thức stream nào khả dụng
                    raise ValueError("Không tìm thấy phương thức streaming phù hợp")
            
            # Save assistant response to database if chat_id is provided
            if chat_id and user_message_id:
                try:
                    # Clean content (remove thinking tags)
                    clean_content = re.sub(r'<thinking>.*?</thinking>', '', full_response, flags=re.DOTALL).strip()
                    
                    # Save assistant message to database
                    assistant_message_id = self.insert_message(
                        chat_id=chat_id,
                        role="ASSISTANT",
                        content=clean_content
                    )
                    
                    if assistant_message_id:
                        # Update lastMessage in Chat
                        self.update_last_message(chat_id, assistant_message_id)
                        logger.info(f"Saved streaming response to database with ID: {assistant_message_id}")
                except Exception as save_err:
                    logger.error(f"Failed to save streaming response to database: {str(save_err)}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}", exc_info=True)
            yield f"I'm sorry, an error occurred while processing your message: {str(e)}"
    
    def _create_file_context(
        self, 
        df: pd.DataFrame, 
        file_path: str, 
        quality_report: Optional[Dict] = None
    ) -> str:
        """
        Create context from DataFrame and quality report
        
        Args:
            df: Loaded DataFrame
            file_path: File path
            quality_report: Data quality report (if any)
            
        Returns:
            str: Context for prompt
        """
        try:
            if df is None or df.empty:
                return f"File appears to be empty: {os.path.basename(file_path)}"
            
            # Basic information
            file_format = os.path.splitext(file_path)[1][1:].upper()
            num_rows = len(df)
            num_cols = len(df.columns)
            columns = df.columns.tolist()
            
            # Sample data
            sample_rows = min(3, len(df))
            sample_data = json.dumps(df.head(sample_rows).to_dict(orient='records'), indent=2)
            
            # Detect column types - use from BaseService
            column_types = self.detect_column_types(df)
            
            # Format column types
            column_type_info = []
            for column_type, cols in column_types.items():
                if cols:
                    col_list = ", ".join(cols[:5])
                    if len(cols) > 5:
                        col_list += f" and {len(cols) - 5} more"
                    column_type_info.append(f"- {column_type.capitalize()}: {col_list}")
            
            column_type_str = "\n".join(column_type_info)
            
            # Add data quality info if present
            quality_info = ""
            if quality_report:
                try:
                    missing_percent = quality_report.get("data_quality", {}).get("completeness", {}).get("missing_percent", 0)
                    overall_score = quality_report.get("data_quality", {}).get("quality_metrics", {}).get("overall_score", 0)
                    
                    quality_info = f"\nData Quality:\n- Overall quality score: {overall_score:.1f}/100\n- Missing data: {missing_percent:.1f}%"
                    
                    # Add main issues
                    issues = quality_report.get("data_quality", {}).get("issues", [])
                    if issues:
                        quality_info += "\nPotential issues:\n" + "\n".join([f"- {issue}" for issue in issues[:3]])
                except Exception as e:
                    logger.warning(f"Error parsing quality report: {str(e)}")
            
            # Create context
            context = textwrap.dedent(f"""\
                File information:
                - Filename: {os.path.basename(file_path)}
                - Format: {file_format}
                - Number of rows: {num_rows}
                - Number of columns: {num_cols}
                - Column names: {', '.join(columns)}

                Column types by category:
                {column_type_str}
                {quality_info}

                Sample data (first {sample_rows} rows):
                {sample_data}
            """)
            return context
        except Exception as e:
            logger.error(f"Error creating file context: {str(e)}", exc_info=True)
            return f"Error creating file context: {str(e)}"
    
    def _extract_commands(self, response: str) -> List[Dict[str, Any]]:
        """
        Extract and parse commands from response
        
        Args:
            response: Model response
            
        Returns:
            List[Dict[str, Any]]: List of commands
        """
        try:
            commands = []
            
            # Function call pattern - common in LangChain agent responses
            func_pattern = r'Action: (\w+)\s*\nAction Input: (.+?)(?=\nObservation:|$)'
            func_matches = re.finditer(func_pattern, response, re.DOTALL)
            for match in func_matches:
                action = match.group(1)
                action_input = match.group(2).strip()
                
                # Map to command type
                cmd_type = None
                if action in ["generate_chart", "generate_visualization", "visualize"]:
                    cmd_type = "visualization"
                elif action in ["generate_insights", "analyze_data"]:
                    cmd_type = "insight"
                else:
                    cmd_type = "tool"
                
                commands.append({
                    "type": cmd_type,
                    "tool": action,
                    "input": action_input,
                    "columns": self._extract_columns_from_input(action_input)
                })
            
            # Visualization command pattern
            viz_patterns = [
                r'(visualize|plot|draw|chart|graph|show|display)\s*\(\s*(?P<params>[^)]+)\)',
                r'(visualize|plot|draw|chart|graph|show|display)\s+(?P<params>[a-zA-Z0-9_,\s]+)',
                r'(create|make|generate)\s+(a|an)?\s*(chart|graph|plot|visualization)\s+(of|for)\s+(?P<params>[a-zA-Z0-9_,\s]+)',
                r'(show|display)\s+(?P<params>[a-zA-Z0-9_,\s]+)\s+(as|in|with|using)\s+(a|an)?\s*(chart|graph|plot|visualization)'
            ]
            
            for pattern in viz_patterns:
                viz_matches = re.finditer(pattern, response, re.IGNORECASE)
                for match in viz_matches:
                    params_str = match.group('params')
                    params = [p.strip() for p in re.split(r'[,\s]+and\s+|\s*,\s*|\s+vs\.?\s+|\s+against\s+|\s+by\s+', params_str)]
                    
                    commands.append({
                        "type": "visualization",
                        "columns": params,
                        "chart_type": "auto"
                    })
            
            # Chart specific command pattern
            chart_pattern = r'(bar|line|scatter|pie|histogram)\s*\(\s*(?P<params>[^)]+)\)'
            chart_matches = re.finditer(chart_pattern, response, re.IGNORECASE)
            
            for match in chart_matches:
                chart_type = match.group(1).lower()
                params_str = match.group('params')
                params = [p.strip() for p in params_str.split(',')]
                
                commands.append({
                    "type": "visualization",
                    "columns": params,
                    "chart_type": chart_type
                })
            
            # Insight command pattern
            insight_pattern = r'(insight|analyze)\s*\(\s*(?P<params>[^)]*)\)'
            insight_matches = re.finditer(insight_pattern, response, re.IGNORECASE)
            
            for match in insight_matches:
                params_str = match.group('params')
                params = [p.strip() for p in params_str.split(',')] if params_str else []
                
                commands.append({
                    "type": "insight",
                    "columns": params
                })
            
            return commands
        except Exception as e:
            logger.error(f"Error extracting commands: {str(e)}", exc_info=True)
            return []
    
    def _extract_columns_from_input(self, action_input: str) -> List[str]:
        """
        Extract column names from action input
        
        Args:
            action_input: Action input string
            
        Returns:
            List[str]: List of column names
        """
        try:
            # Try to parse as JSON
            try:
                data = json.loads(action_input)
                if isinstance(data, dict) and "columns" in data:
                    return data["columns"]
                elif "column" in data:
                    return [data["column"]]
            except:
                pass
            
            # Try to extract from string
            columns = []
            col_pattern = r'(?:columns|column|using)[\s:]+([\w\s,]+)'
            col_match = re.search(col_pattern, action_input, re.IGNORECASE)
            if col_match:
                col_str = col_match.group(1)
                columns = [c.strip() for c in re.split(r'[,\s]+and\s+|\s*,\s*', col_str)]
            
            return columns
        except Exception as e:
            logger.error(f"Error extracting columns from action input: {str(e)}", exc_info=True)
            return []
    
    def _create_analyze_service(self, file_id: str, user_id: str) -> AnalyzeService:
        """
        Create instance of AnalyzeService
        
        Args:
            file_id: File ID
            user_id: User ID
            
        Returns:
            AnalyzeService: Instance of AnalyzeService
        """
        return AnalyzeService(
            file_id=file_id,
            user_id=user_id,
            model_service=self.model_service,
            intent_service=self.intent_service,
            validation_service=self.validation_service,
            config=self.config
        )
        
    async def _generate_visualizations(
        self,
        analyze_service: AnalyzeService,
        df: pd.DataFrame,
        response: str,
        query: str,
        commands: List[Dict[str, Any]] = None,
        intent: Optional[UserIntent] = None
    ) -> List[VisualizationData]:
        """
        Create visualizations using AnalyzeService
        
        Args:
            analyze_service: AnalyzeService instance
            df: Loaded DataFrame
            response: Model response
            query: Original query
            commands: Extracted commands
            intent: Detected intent
            
        Returns:
            List[VisualizationData]: Created visualizations
        """
        try:
            logger.info(f"Generating visualizations for query: '{query}'")
            
            if df is None or df.empty:
                logger.warning("DataFrame is empty or None")
                return None
                    
            # Prioritize columns from commands
            columns_to_use = []
            chart_type = None
            
            # 1. Extract from commands
            if commands:
                viz_commands = [cmd for cmd in commands if cmd.get("type") == "visualization"]
                if viz_commands:
                    columns_to_use = viz_commands[0].get("columns", [])
                    chart_type = viz_commands[0].get("chart_type")
            
            # 2. Use intent if available and no columns from commands
            if not columns_to_use and intent and intent.columns:
                columns_to_use = intent.columns
                chart_type = intent.visualization_type
            
            # 3. Extract from query and response if still no columns
            if not columns_to_use:
                extracted_columns, extracted_chart_type = self._extract_visualization_info(query, response, df.columns)
                if extracted_columns:
                    columns_to_use = extracted_columns
                    chart_type = extracted_chart_type or chart_type
            
            # 4. Use visualization-specific method from analyze_service
            if columns_to_use:
                # Ensure columns exist in DataFrame
                valid_columns = [col for col in columns_to_use if col in df.columns]
                if valid_columns:
                    # Convert chart_type to ChartType enum if specified
                    chart_types = None
                    if chart_type:
                        if chart_type == "bar":
                            chart_types = [ChartType.BAR]
                        elif chart_type == "line":
                            chart_types = [ChartType.LINE]
                        elif chart_type == "scatter":
                            chart_types = [ChartType.SCATTER]
                        elif chart_type == "pie":
                            chart_types = [ChartType.PIE]
                        elif chart_type == "histogram":
                            chart_types = [ChartType.HISTOGRAM]
                        elif chart_type == "heatmap":
                            chart_types = [ChartType.HEATMAP]
                        elif chart_type == "box":
                            chart_types = [ChartType.BOX]
                
                    # Pass query to provide context
                    return await analyze_service.generate_visualizations(df[valid_columns], chart_types, query)
            
            # 5. Fallback to automatic visualization
            logger.info("Using automatic visualization generation")
            return await analyze_service.generate_visualizations(df, None, query)
        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}", exc_info=True)
            return None
        
    def _extract_visualization_info(
        self, 
        query: str, 
        response: str, 
        available_columns: List[str]
    ) -> Tuple[List[str], Optional[str]]:
        """
        Extract column and chart type info from query and response
        
        Args:
            query: User query
            response: Model response
            available_columns: Available column names
            
        Returns:
            Tuple[List[str], Optional[str]]: Columns and chart type
        """
        try:
            # Combine query and response for analysis
            text = (query + " " + response).lower()
            
            # Find mentioned columns
            mentioned_columns = []
            for col in available_columns:
                col_lower = col.lower()
                if re.search(r'\b' + re.escape(col_lower) + r'\b', text):
                    mentioned_columns.append(col)
            
            if not mentioned_columns:
                common_columns = {
                    'date': ['date', 'time', 'year', 'month', 'day'],
                    'numeric': ['sales', 'revenue', 'price', 'cost', 'profit', 'amount', 'count', 'value', 'score'],
                    'categorical': ['category', 'product', 'customer', 'region', 'country', 'state', 'city', 'type', 'status']
                }
                
                for col in available_columns:
                    col_lower = col.lower()
                    for terms in common_columns.values():
                        if any(term in col_lower for term in terms) and col not in mentioned_columns:
                            mentioned_columns.append(col)
                            
            # Limit to max 3 columns
            if len(mentioned_columns) > 3:
                mentioned_columns = mentioned_columns[:3]

            # Detect chart type
            chart_types = {
                "bar": ["bar", "column", "barchart", "columns", "bars"],
                "line": ["line", "trend", "linechart", "timeseries", "time series"],
                "scatter": ["scatter", "scatterplot", "correlation", "correlate"],
                "pie": ["pie", "piechart", "percentage", "proportion"],
                "histogram": ["histogram", "distribution", "frequency"],
                "box": ["box", "boxplot", "whisker", "outlier"],
                "heatmap": ["heatmap", "heat", "matrix", "correlation matrix"],
                "area": ["area", "areachart", "stacked area"]
            }
            
            chart_type = None
            for ct, keywords in chart_types.items():
                for keyword in keywords:
                    if keyword in text:
                        chart_type = ct
                        break
                if chart_type:
                    break
            
            return mentioned_columns, chart_type
        except Exception as e:
            logger.error(f"Error extracting visualization info: {str(e)}", exc_info=True)
            return [], None
        
    async def _generate_insights(
        self,
        analyze_service: AnalyzeService,
        df: pd.DataFrame,
        query: str,
        commands: List[Dict[str, Any]] = None,
        intent: Optional[UserIntent] = None
    ) -> List[InsightData]:
        """
        Generate insights using AnalyzeService
        
        Args:
            analyze_service: AnalyzeService instance
            df: Loaded DataFrame
            response: Model response
            query: Original query
            commands: Extracted commands
            intent: Detected intent
            
        Returns:
            List[InsightData]: Generated insights
        """
        try:
            if df is None or df.empty:
                logger.warning("DataFrame is empty or None")
                return None
                    
            # Determine insight types based on intent and query
            insight_types = None
            
            # 1. Extract from commands
            columns_to_focus = None
            if commands:
                insight_commands = [cmd for cmd in commands if cmd.get("type") == "insight"]
                if insight_commands and insight_commands[0].get("columns"):
                    columns_to_focus = insight_commands[0].get("columns")
            
            # 2. Extract from intent
            if intent and intent.intent in [IntentType.INSIGHT, IntentType.ANALYSIS]:
                if intent.columns:
                    columns_to_focus = intent.columns
                
                # Extract insight types from query
                if "correlation" in query.lower():
                    insight_types = ["CORRELATION"]
                elif "trend" in query.lower() or "time" in query.lower():
                    insight_types = ["TREND"]
                elif "outlier" in query.lower() or "anomaly" in query.lower():
                    insight_types = ["OUTLIER"]
                elif "distribution" in query.lower():
                    insight_types = ["DISTRIBUTION"]
                elif "pattern" in query.lower():
                    insight_types = ["PATTERN"]
            
            # Ensure columns exist in DataFrame
            if columns_to_focus:
                columns_to_focus = [col for col in columns_to_focus if col in df.columns]
                if columns_to_focus:
                    df = df[columns_to_focus]
            
            # Generate insights with analyze_service
            insights = await analyze_service.generate_insights(df, insight_types, query)
            
            # Limit number of insights
            return insights[:5] if insights else None
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}", exc_info=True)
            return None

    async def clear_user_conversation(self, user_id: str) -> bool:
        """
        Clear user conversation history
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if successful
        """
        try:
            # Clear conversation ID from map
            if user_id in self._conversation_map:
                conversation_id = self._conversation_map[user_id]
                
                # Clear from model service
                if hasattr(self.model_service, "clear_conversation"):
                    self.model_service.clear_conversation(conversation_id)
                
                # Remove from map
                del self._conversation_map[user_id]
                
                logger.info(f"Cleared conversation history for user: {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error clearing user conversation: {str(e)}", exc_info=True)
            return False
    
    def _convert_numpy_types(self, obj):
        """
        Convert NumPy types to Python native types for serialization
        
        Args:
            obj: Object to convert
            
        Returns:
            Object with NumPy types converted
        """
        if isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: self._convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(i) for i in obj]
        elif isinstance(obj, tuple):
            return tuple(self._convert_numpy_types(i) for i in obj)
        else:
            return obj

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for chat service with more detailed information
        
        Returns:
            Dict[str, Any]: Health status
        """
        try:
            # Check ModelService
            model_status = {
                "loaded": False,
                "error": None
            }
            
            try:
                if hasattr(self.model_service, "model_loaded"):
                    model_status["loaded"] = self.model_service.model_loaded
                elif hasattr(self.model_service, "_model_loaded"):
                    model_status["loaded"] = self.model_service._model_loaded
                else:
                    # Fallback check - try calling a simple method
                    system_info = self.model_service.get_system_info()
                    model_status["loaded"] = True
                    model_status["system_info"] = system_info
            except Exception as model_e:
                model_status["error"] = str(model_e)
            
            # Check other services
            services_status = {
                "intent_service": self.intent_service is not None,
                "validation_service": self.validation_service is not None,
                "config": bool(self._config),
                "langchain_enabled": self._config.get('use_langchain_agent', True)
            }
            
            # Check LangChain status
            langchain_status = {
                "enabled": False,
                "memory_count": 0,
                "agent_count": 0
            }
            
            try:
                if hasattr(self.model_service, "_langchain_model"):
                    langchain_status["enabled"] = self.model_service._langchain_model is not None
                
                if hasattr(self.model_service, "_langchain_memory"):
                    langchain_status["memory_count"] = len(self.model_service._langchain_memory)
                
                if hasattr(self.model_service, "_langchain_agents"):
                    langchain_status["agent_count"] = len(self.model_service._langchain_agents)
                
                if hasattr(self.model_service, "_function_registry"):
                    langchain_status["functions_registered"] = len(self.model_service._function_registry)
            except Exception as e:
                langchain_status["error"] = str(e)
            
            # Cache information
            cache_status = {}
            if hasattr(self.cache, "get_stats"):
                cache_status = self.cache.get_stats()
            else:
                cache_status = {
                    "enabled": self.cache is not None,
                    "file_context_keys": len(self.file_context_cache)
                }
            
            # System resource information
            resource_info = self._get_system_resources()
            
            return {
                "status": "healthy",
                "model": model_status,
                "services": services_status,
                "langchain": langchain_status,
                "cache": cache_status,
                "active_conversations": len(self._conversation_map),
                "resources": resource_info,
                "version": "3.0.0"
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}", exc_info=True)
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def semantic_search_in_file(
        self,
        query: str,
        file_id: Optional[str] = None,
        file_path: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Thực hiện tìm kiếm ngữ nghĩa trong file dữ liệu
        
        Args:
            query: Câu truy vấn tìm kiếm
            file_id: ID của file
            file_path: Đường dẫn đến file
            top_k: Số lượng kết quả trả về
            
        Returns:
            List[Dict[str, Any]]: Danh sách kết quả tìm kiếm với điểm tương đồng
        """
        try:
            if not file_path:
                raise ValueError("file_path is required for semantic search")
                
            # Đảm bảo model_service có sẵn
            if not self.model_service:
                raise ValueError("model_service not available")
                
            # Tải file dữ liệu
            if self.validation_service:
                df, _ = await self.validation_service.load_and_validate_data(
                    file_path, sample=False, max_rows=10000  # Giới hạn 10K dòng cho tìm kiếm
                )
            else:
                # Fallback nếu không có validation_service
                import pandas as pd
                df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
                
            if df.empty:
                return []
                
            # Chuyển đổi dòng dữ liệu thành các văn bản
            documents = []
            for idx, row in df.iterrows():
                # Tạo văn bản bằng cách kết hợp tên cột và giá trị
                doc = ", ".join([f"{col}: {row[col]}" for col in df.columns])
                documents.append(doc)
                
            # Đảm bảo không quá nhiều documents để tránh quá tải bộ nhớ
            max_docs = 1000
            if len(documents) > max_docs:
                documents = documents[:max_docs]
                
            # Tạo embeddings cho các văn bản sử dụng model_service
            document_embeddings = self.model_service.get_embeddings(documents)
            
            # Tạo embedding cho câu truy vấn
            query_embedding = self.model_service.get_embeddings([query])[0]
            
            # Tính toán điểm tương đồng cosine
            import numpy as np
            from scipy.spatial.distance import cosine
            
            similarities = []
            for idx, doc_embedding in enumerate(document_embeddings):
                # Tính khoảng cách cosine (1 - cosine = similarity)
                similarity = 1 - cosine(query_embedding, doc_embedding)
                similarities.append((idx, similarity))
                
            # Sắp xếp kết quả theo độ tương đồng giảm dần và lấy top-k
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_results = similarities[:top_k]
            
            # Tạo danh sách kết quả với dữ liệu đầy đủ
            results = []
            for idx, score in top_results:
                if 0 <= idx < len(df):
                    # Chuyển đổi dữ liệu dòng thành dictionary
                    row_data = df.iloc[idx].to_dict()
                    
                    # Loại bỏ các kiểu dữ liệu NumPy
                    row_data = self._convert_numpy_types(row_data)
                    
                    results.append({
                        "row_index": int(idx),
                        "score": float(score),
                        "data": row_data,
                        "text": documents[idx][:200] + "..." if len(documents[idx]) > 200 else documents[idx]
                    })
                    
            return results
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}", exc_info=True)
            raise

    def _get_system_resources(self) -> Dict[str, Any]:
        """
        Get system resource information
        
        Returns:
            Dict[str, Any]: Resource information
        """
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024 ** 3)
            memory_total_gb = memory.total / (1024 ** 3)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024 ** 3)
            disk_total_gb = disk.total / (1024 ** 3)
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_used_gb": round(memory_used_gb, 2),
                "memory_total_gb": round(memory_total_gb, 2),
                "disk_percent": disk_percent,
                "disk_used_gb": round(disk_used_gb, 2),
                "disk_total_gb": round(disk_total_gb, 2)
            }
        except Exception as e:
            logger.error(f"Error getting system resources: {str(e)}")
            return {"error": str(e)}