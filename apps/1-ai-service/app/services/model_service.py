# app/services/model_service.py
import logging
import threading
import time
import hashlib
import json
import contextlib
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List, ClassVar
from pydantic import Field

import torch
import pandas as pd

from app.core.config import ModelConfig
from app.core.cache import InferenceCache
from app.services.intent_service import IntentDetectionService
from app.services.base_service import BaseService

# Import from ml module
from ml.model.mistral_inference import MistralInference
from ml.utils.memory_utils import check_memory_usage
from ml.data.data_processor import DataProcessor
from ml.analysis.analyzer import DataAnalyzer
from ml.visualization.charts import ChartGenerator
from ml.visualization.insights import InsightGenerator
from ml.tools.langchain_agent_factory import LangChainAgentFactory
from ml.tools.postgres_connector import PostgreSQLConnector
from ml.tools.data_analysis_tools import DataAnalysisTools

# Import LangChain components
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent, AgentType, Tool

# Import custom LangChain utilities
from langchain.callbacks.manager import CallbackManager

logger = logging.getLogger(__name__)

class ModelService(BaseService):
    """Service for LLM Model integrated with ML architecture and LangChain"""
    
    _instance = None
    _initialized = False
    _model_loaded = False
    _model_loading = False

    @classmethod
    def get_instance(cls, config: Optional[ModelConfig] = None, cache: Optional[InferenceCache] = None):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = ModelService(config=config, cache=cache)
        return cls._instance
    
    def __init__(self, config: Optional[ModelConfig] = None, cache: Optional[InferenceCache] = None):
        """Initialize service with ML integration"""
        super().__init__(config=config)
        
        if not ModelService._initialized:
            # Configuration and cache
            self.config = config or ModelConfig()
            self.cache = cache or InferenceCache()
            
            # Integration with intent service
            self.data_analysis_tools = None
            self.postgres_connector = None
            self.langchain_agent_factory = None
            self.intent_service = IntentDetectionService.get_instance(self.config.config)
            
            # Mistral Inference Engine from ML module - lazy init
            self._mistral = None

            # PostgreSQL connection
            self.pg_dsn = "postgresql://ecommerce:ecommerce@localhost:5432/datasense"
            self._db_connection = None
            
            # Function registry for tool usage
            self._function_registry = {}
            
            # LangChain components
            self._langchain_model = None
            self._langchain_memory = {}  # Dict to store memory per conversation
            self._langchain_agents = {}  # Dict to store agents per conversation
            
            # ML analysis tools
            self._data_processor = None
            self._data_analyzer = None
            self._chart_generator = None
            self._insight_generator = None
            
            # Memory management
            self._model_load_lock = threading.Lock()
            
            # Lazy load flag
            self._lazy_load = self.config.get_model_config().get("lazy_load", True)
            
            # Start time
            self._start_time = time.time()
            
            # Mark as initialized
            ModelService._initialized = True
            
            logger.info("Model service initialized with LangChain integration")
            
            # If not lazy load, load model now
            if not self._lazy_load:
                self._ensure_model_loaded()
    
    @property
    def mistral(self) -> MistralInference:
        """Lazy initialize and return Mistral Inference Engine"""
        if self._mistral is None:
            logger.info("Initializing MistralInference engine")
            self._mistral = MistralInference(self.config.config)
            
            # Register functions after initialization
            self._register_default_functions()
        return self._mistral
    
    @property
    def data_processor(self) -> DataProcessor:
        """Lazy initialize and return DataProcessor"""
        if self._data_processor is None:
            logger.info("Initializing DataProcessor")
            self._data_processor = DataProcessor()
        return self._data_processor
    
    @property
    def data_analyzer(self) -> DataAnalyzer:
        """Lazy initialize and return DataAnalyzer"""
        if self._data_analyzer is None:
            logger.info("Initializing DataAnalyzer")
            self._data_analyzer = DataAnalyzer()
        return self._data_analyzer
    
    @property
    def chart_generator(self) -> ChartGenerator:
        """Lazy initialize and return ChartGenerator"""
        if self._chart_generator is None:
            logger.info("Initializing ChartGenerator")
            self._chart_generator = ChartGenerator()
        return self._chart_generator
    
    @property
    def insight_generator(self) -> InsightGenerator:
        """Lazy initialize and return InsightGenerator"""
        if self._insight_generator is None:
            logger.info("Initializing InsightGenerator")
            self._insight_generator = InsightGenerator()
        return self._insight_generator
    
    @property
    def model_loaded(self) -> bool:
        """Check if model is loaded"""
        if self._mistral is None:
            return False
        return self.mistral.manager.is_model_available
    
    @property
    def model(self):
        """Get model with lazy loading"""
        self._ensure_model_loaded()
        return self.mistral.model_container["model"] if self.mistral.model_container else None
    
    @property
    def tokenizer(self):
        """Get tokenizer with lazy loading"""
        self._ensure_model_loaded()
        return self.mistral.model_container["tokenizer"] if self.mistral.model_container else None
    
    @contextlib.contextmanager
    def inference_context(self):
        """Context manager to ensure resources are released after inference"""
        torch_device = None
        try:
            # Ensure model is loaded
            self._ensure_model_loaded()
            
            # Prepare GPU
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch_device = torch.device("cuda")
            
            # Yield model context
            yield {
                "model": self.model,
                "tokenizer": self.tokenizer,
                "device": torch_device or "cpu",
                "mistral": self.mistral
            }
        finally:
            # Ensure GPU memory is released
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def _ensure_model_loaded(self):
        """Ensure model is loaded with better memory management"""
        # If model already loaded, return immediately
        if self.model_loaded:
            return
            
        # Use lock to prevent multiple threads from loading model
        with self._model_load_lock:
            # Check again after lock
            if self.model_loaded:
                return
                
            # If loading, wait
            if ModelService._model_loading:
                logger.info("Model is being loaded by another thread, waiting...")
                while ModelService._model_loading:
                    time.sleep(0.5)
                return
                
            # Mark as loading
            ModelService._model_loading = True
            
            try:
                # Time model loading
                start_time = time.time()
                
                logger.info("Loading Mistral model...")
                
                # Free memory before loading
                import gc
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                # Check and limit VRAM/RAM usage
                memory_info = check_memory_usage()
                available_memory_gb = memory_info["memory"]["available_gb"]
                logger.info(f"Available memory: {available_memory_gb:.2f} GB")
                
                # Adjust config based on memory
                if available_memory_gb < 4.0:  # Less than 4GB
                    # Update config to use 4-bit quantization
                    model_config = self.config.config.get("model", {})
                    model_config["load_in_4bit"] = True
                    model_config["load_in_8bit"] = False
                    logger.info("Limited memory detected, forcing 4-bit quantization")
                
                # Load model using MistralInference from ML module
                self.mistral.load_model(force_reload=False)
                
                # Log loading time
                load_time = time.time() - start_time
                logger.info(f"Model loaded successfully in {load_time:.2f} seconds")
                
                # Create LangChain model
                self._create_langchain_model()
                
                # Register default functions
                self._register_default_functions()
                
            except Exception as e:
                logger.error(f"Error loading model: {str(e)}", exc_info=True)
                raise
            finally:
                ModelService._model_loading = False
                
        if self.model_loaded and not self.data_analysis_tools:
            self.data_analysis_tools = DataAnalysisTools(self.pg_dsn)
            self.postgres_connector = PostgreSQLConnector(self.pg_dsn)
            
            # Khởi tạo LangChain agent factory sau khi có model
            if self._langchain_model:
                self.langchain_agent_factory = LangChainAgentFactory(
                    llm=self._langchain_model,
                    db_connection_string=self.pg_dsn
                )
    
    def _create_langchain_model(self):
        """Create LangChain model from Mistral"""
        try:
            from langchain.llms.base import LLM
            
            class MistralLLM(LLM):
                """LangChain compatible LLM using MistralInference"""
                
                # Use ClassVar to indicate this is a class-level attribute
                mistral_inference: ClassVar[Optional[MistralInference]] = None
                
                # Properly annotated fields with Pydantic
                model_name: str = Field(default="Mistral")
                temperature: float = Field(default=0.7)
                max_tokens: int = Field(default=2048)
                
                def __init__(self, mistral_inference, **kwargs):
                    """Initialize with MistralInference instance"""
                    # Use super().__init__ with explicit conversion to dict
                    super().__init__(**{k: v for k, v in kwargs.items() if k in ['temperature', 'max_tokens']})
                    
                    # Assign mistral_inference as a class variable
                    MistralLLM.mistral_inference = mistral_inference
                    
                    # Override default values if provided in kwargs
                    if 'temperature' in kwargs:
                        self.temperature = kwargs['temperature']
                    if 'max_tokens' in kwargs:
                        self.max_tokens = kwargs['max_tokens']
                
                @property
                def _llm_type(self) -> str:
                    """Return type of LLM."""
                    return "mistral"
                
                def _call(
                    self, 
                    prompt: str, 
                    stop: Optional[List[str]] = None,
                    run_manager=None,
                    **kwargs
                ) -> str:
                    """Call the Mistral model with the given prompt."""
                    try:
                        # Ensure mistral_inference is available
                        if not MistralLLM.mistral_inference:
                            raise ValueError("Mistral inference not initialized")
                        
                        # Generate response using mistral_inference
                        params = {
                            "temperature": self.temperature,
                            "max_tokens": self.max_tokens,
                        }
                        
                        # Add any additional parameters
                        params.update(kwargs)
                        
                        # Add stop sequences if provided
                        if stop:
                            params["stop_sequences"] = stop
                        
                        # Generate using mistral (without KV cache)
                        response = MistralLLM.mistral_inference.generate(
                            prompt=prompt,
                            use_history=False,  # Don't use internal history - LangChain handles this
                            **params
                        )
                        
                        return response
                    except Exception as e:
                        logger.error(f"Error in MistralLLM._call: {str(e)}", exc_info=True)
                        return f"Error generating response: {str(e)}"

                @property
                def _identifying_params(self) -> Dict[str, Any]:
                    """Return identifying parameters."""
                    return {
                        "model_name": self.model_name,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens
                    }
            
            # Create LangChain model
            self._langchain_model = MistralLLM(
                mistral_inference=self.mistral,
                temperature=0.7,
                max_tokens=2048
            )
            
            logger.info("LangChain model created successfully")
        except Exception as e:
            logger.error(f"Error creating LangChain model: {str(e)}", exc_info=True)
            self._langchain_model = None
    
    def _register_default_functions(self):
        """Register default functions for tool usage"""
        try:
            # Data processing functions
            self.register_function(
                name="process_data",
                func=self._process_data,
                description="Process data using DataProcessor. Cleans and normalizes data."
            )
            
            # Data analysis functions
            self.register_function(
                name="analyze_data",
                func=self._analyze_data,
                description="Analyze data using DataAnalyzer. Provides statistical analysis and insights."
            )
            
            # Visualization functions
            self.register_function(
                name="generate_chart",
                func=self._generate_chart,
                description="Generate a chart visualization from data."
            )
            
            # Insight functions
            self.register_function(
                name="generate_insights",
                func=self._generate_insights,
                description="Generate insights from data."
            )
            
            # PostgreSQL functions
            self.register_function(
                name="execute_sql",
                func=self._execute_sql,
                description="Execute SQL query on PostgreSQL database."
            )
            
            self.register_function(
                name="describe_database",
                func=self._describe_database,
                description="Get information about database schema."
            )
            
            logger.info("Default functions registered successfully")
        except Exception as e:
            logger.error(f"Error registering default functions: {str(e)}", exc_info=True)
    
    def register_function(self, name: str, func: callable, description: str, parameters: Dict = None):
        """Register a function that can be called"""
        try:
            # Register with mistral
            if hasattr(self.mistral, 'register_function'):
                self.mistral.register_function(name, func, description, parameters)
            
            # Also register in our function registry
            self._function_registry[name] = {
                "function": func,
                "description": description,
                "parameters": parameters or {}
            }
            
            logger.info(f"Registered function: {name}")
        except Exception as e:
            logger.error(f"Error registering function {name}: {str(e)}", exc_info=True)
    
    def _process_data(self, data_str: str) -> str:
        """Process data using DataProcessor"""
        try:
            # Convert data string to DataFrame
            df = None
            try:
                # Try JSON format first
                df = pd.read_json(data_str)
            except:
                # Try CSV format
                import io
                df = pd.read_csv(io.StringIO(data_str))
            
            if df is None:
                return "Error: Failed to parse data string"
            
            # Process data
            processed_df = self.data_processor.process(df)
            
            # Convert result to string
            return processed_df.to_string()
        except Exception as e:
            logger.error(f"Error processing data: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
    
    def _analyze_data(self, data_str: str, analysis_type: str = "full") -> str:
        """Analyze data using DataAnalyzer"""
        try:
            # Convert data string to DataFrame
            df = None
            try:
                # Try JSON format first
                df = pd.read_json(data_str)
            except:
                # Try CSV format
                import io
                df = pd.read_csv(io.StringIO(data_str))
            
            if df is None:
                return "Error: Failed to parse data string"
            
            # Analyze data
            analysis_results = self.data_analyzer.run_analysis(df, analysis_type=analysis_type)
            
            # Convert result to string
            return json.dumps(analysis_results, indent=2)
        except Exception as e:
            logger.error(f"Error analyzing data: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
    
    def _generate_chart(self, data_str: str, chart_type: str = None, columns: List[str] = None) -> str:
        """Generate chart visualization from data"""
        try:
            # Convert data string to DataFrame
            df = None
            try:
                # Try JSON format first
                df = pd.read_json(data_str)
            except:
                # Try CSV format
                import io
                df = pd.read_csv(io.StringIO(data_str))
            
            if df is None:
                return "Error: Failed to parse data string"
            
            # Filter columns if specified
            if columns:
                valid_columns = [col for col in columns if col in df.columns]
                if valid_columns:
                    df = df[valid_columns]
            
            # Generate charts
            chart_types = [chart_type] if chart_type else None
            
            # Use ChartRecommender to get best chart type if not specified
            if chart_types is None:
                recommender = self.insight_generator.chart_recommender
                if recommender:
                    recommendations = recommender.recommend_charts(df, columns)
                    if recommendations:
                        # Get best chart type
                        best_charts = recommender.get_best_charts(df, columns)
                        if best_charts and len(best_charts) > 0:
                            chart_types = [best_charts[0].get("type")]
            
            # Create visualization
            charts = self.chart_generator.generate_automatic_charts(df, chart_types=chart_types)
            
            # Convert to descriptive string
            result = []
            for i, chart in enumerate(charts):
                result.append(f"Chart {i+1}:")
                result.append(f"Type: {chart.get('type')}")
                result.append(f"Title: {chart.get('title')}")
                result.append(f"Description: {chart.get('description')}")
                result.append("")
            
            return "\n".join(result)
        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
    
    def _generate_insights(self, data_str: str, insight_types: List[str] = None) -> str:
        """Generate insights from data"""
        try:
            # Convert data string to DataFrame
            df = None
            try:
                # Try JSON format first
                df = pd.read_json(data_str)
            except:
                # Try CSV format
                import io
                df = pd.read_csv(io.StringIO(data_str))
            
            if df is None:
                return "Error: Failed to parse data string"
            
            # Generate insights
            insights = self.insight_generator.generate_rule_based_insights(df, None, insight_types)
            
            # Convert to descriptive string
            result = []
            for i, insight in enumerate(insights):
                result.append(f"Insight {i+1}:")
                result.append(f"Type: {insight.get('type')}")
                result.append(f"Title: {insight.get('title')}")
                result.append(f"Content: {insight.get('content')}")
                result.append(f"Importance: {insight.get('importance')}")
                result.append("")
            
            return "\n".join(result)
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
    
    def _execute_sql(self, query: str) -> str:
        """Execute SQL query on PostgreSQL database"""
        try:
            import psycopg2
            import pandas as pd
            
            # Connect to database
            conn = psycopg2.connect(self.pg_dsn)
            
            # Execute query
            df = pd.read_sql_query(query, conn)
            
            # Close connection
            conn.close()
            
            # Return results
            if len(df) == 0:
                return "No results found."
            
            # Limit rows for large results
            max_rows = 100
            if len(df) > max_rows:
                result = df.head(max_rows).to_string() + f"\n\n[Showing {max_rows} of {len(df)} rows]"
            else:
                result = df.to_string()
            
            return result
        except Exception as e:
            logger.error(f"Error executing SQL query: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
    
    def _describe_database(self) -> str:
        """Get information about database schema"""
        try:
            import psycopg2
            
            # Connect to database
            conn = psycopg2.connect(self.pg_dsn)
            cursor = conn.cursor()
            
            # Query to list all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            
            # Get schema for each table
            result = []
            for table in tables:
                table_name = table[0]
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position;
                """)
                
                columns = cursor.fetchall()
                
                # Format table schema
                table_info = f"Table: {table_name}\n"
                table_info += "Columns:\n"
                for col in columns:
                    table_info += f"  - {col[0]} ({col[1]}, Nullable: {col[2]})\n"
                    
                result.append(table_info)
            
            # Close connection
            cursor.close()
            conn.close()
            
            return "\n".join(result)
        except Exception as e:
            logger.error(f"Error describing database: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
    
    def get_function_registry(self) -> Dict[str, Dict]:
        """Get function registry"""
        return self._function_registry
    
    def get_langchain_tools(self) -> List[Tool]:
        """Get LangChain tools from function registry"""
        tools = []
        for name, func_info in self._function_registry.items():
            tools.append(Tool(
                name=name,
                func=func_info["function"],
                description=func_info["description"]
            ))
        
        return tools
    
    def create_langchain_agent(self, conversation_id: str, streaming_callback=None) -> Any:
        """Create a LangChain agent for the conversation"""
        try:
            # Ensure model is loaded
            self._ensure_model_loaded()
            
            # Create memory for conversation if not exists
            if conversation_id not in self._langchain_memory:
                chat_history = InMemoryChatMessageHistory()
                memory = ConversationBufferMemory(
                    memory_key='chat_history',
                    return_messages=True,
                    chat_memory=chat_history
                )
                self._langchain_memory[conversation_id] = memory
            
            # Get tools
            tools = self.get_langchain_tools()
            
            # Create callback manager if streaming is enabled
            callback_manager = None
            if streaming_callback:
                from langchain.callbacks.base import BaseCallbackHandler
                
                class StreamingCallbackHandler(BaseCallbackHandler):
                    def __init__(self, streaming_callback):
                        self.streaming_callback = streaming_callback
                        self.buffer = ""
                        self.buffer_size = 5  # Số token tối đa trước khi flush
                        
                    def on_llm_new_token(self, token: str, **kwargs):
                        # Thêm token vào buffer
                        self.buffer += token
                        
                        # Nếu đủ buffer_size token hoặc gặp newline, flush buffer
                        if len(self.buffer) >= self.buffer_size or '\n' in token:
                            self.streaming_callback(self.buffer, False)
                            self.buffer = ""
                        
                    def on_llm_end(self, response, **kwargs):
                        # Đảm bảo flush buffer cuối cùng
                        if self.buffer:
                            self.streaming_callback(self.buffer, False)
                            self.buffer = ""
                        self.streaming_callback("", True)
                    
                    # Thêm hàm xử lý bước trung gian
                    def on_agent_action(self, action, **kwargs):
                        action_str = f"\n<thinking>Using tool: {action.tool}\nInput: {action.tool_input}</thinking>\n"

                        if asyncio.iscoroutinefunction(self.streaming_callback):
                            # Nếu callback là async, chạy nó trong event loop hiện tại
                            asyncio.run_coroutine_threadsafe(
                                self.streaming_callback(action_str, False),
                                asyncio.get_event_loop()
                            )
                        else:
                            self.streaming_callback(action_str, False)
                
                callback_manager = CallbackManager([StreamingCallbackHandler(streaming_callback)])
            
            # Create agent
            agent = initialize_agent(
                tools,
                self._langchain_model,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,  # Thử loại agent khác
                verbose=True,
                memory=self._langchain_memory[conversation_id],
                callback_manager=callback_manager,
                handle_parsing_errors=True,
                # Thêm các tham số sau
                early_stopping_method="generate",  # Sẽ giúp streaming hoạt động tốt hơn
                max_iterations=3,  # Giới hạn số lần lặp để tránh treo
                return_intermediate_steps=True  # Trả về từng bước để có thể stream
            )

            # Store agent
            self._langchain_agents[conversation_id] = agent
            
            return agent
        except Exception as e:
            logger.error(f"Error creating LangChain agent: {str(e)}", exc_info=True)
            return None
    
    def get_langchain_agent(self, conversation_id: str) -> Any:
        """Get LangChain agent for the conversation"""
        if conversation_id in self._langchain_agents:
            return self._langchain_agents[conversation_id]
        return None
    
    def run_langchain_agent(self, conversation_id: str, query: str, streaming_callback=None) -> str:
        """Run LangChain agent with query"""
        try:
            # Get or create agent
            agent = self.get_langchain_agent(conversation_id)
            if not agent:
                agent = self.create_langchain_agent(conversation_id, streaming_callback)
            
            if conversation_id not in self._langchain_memory:
                chat_history = InMemoryChatMessageHistory()
                memory = ConversationBufferMemory(
                    memory_key='chat_history',
                    return_messages=True,
                    chat_memory=chat_history
                )
                
                self._langchain_memory[conversation_id] = memory
                    
            # Get chat history from memory
            chat_history = self._langchain_memory[conversation_id].chat_memory.messages
            
            # Run agent with compatibility for different LangChain versions
            try:
                if hasattr(agent, 'invoke'):
                    result = agent.invoke({
                        "input": query, 
                        "chat_history": chat_history
                    })
                    # Extract 'output' from result if it's a dictionary
                    if isinstance(result, dict) and 'output' in result:
                        return result['output']
                    return str(result)
                else:
                    # Fallback for older versions
                    return agent.run(input=query)
            except AttributeError:
                # Try other possible method names
                if hasattr(agent, '__call__'):
                    result = agent(query)
                    if isinstance(result, dict) and 'output' in result:
                        return result['output']
                    return str(result)
                elif hasattr(agent, 'execute'):
                    result = agent.execute(query)
                    if isinstance(result, dict) and 'output' in result:
                        return result['output']
                    return str(result)
                else:
                    raise Exception("Agent doesn't have compatible execution method")
            
        except Exception as e:
            logger.error(f"Error running LangChain agent: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
    
    async def run_langchain_agent_async(self, conversation_id: str, query: str, streaming_callback=None) -> AsyncGenerator[str, None]:
        """Run LangChain agent asynchronously with streaming"""
        try:
            # Get or create agent
            agent = self.get_langchain_agent(conversation_id)
            if not agent:
                agent = self.create_langchain_agent(conversation_id, streaming_callback)
            
            # Define a streaming callback that yields output
            tokens = []
            
            def callback(token, finished):
                tokens.append((token, finished))
            
            # Run agent in separate thread to avoid blocking
            import threading
            
            def run_agent():
                try:
                    chat_history = []
                    if conversation_id in self._langchain_memory:
                        memory = self._langchain_memory[conversation_id]
                        # Lấy messages từ memory.chat_memory
                        if hasattr(memory, "chat_memory") and hasattr(memory.chat_memory, "messages"):
                            chat_history = memory.chat_memory.messages
                    # Use the updated run_langchain_agent method that handles different API versions
                    if hasattr(agent, 'invoke'):
                        agent.invoke(
                            {
                                "input": query,
                                "chat_history": chat_history
                            }, 
                            callbacks=[callback]
                        )
                    else:
                        self.run_langchain_agent(conversation_id, query, callback)
                except Exception as e:
                    logger.error(f"Error in agent thread: {str(e)}", exc_info=True)
                    callback(f"Error: {str(e)}", True)
            
            result_thread = threading.Thread(target=run_agent)
            result_thread.start()
            
            # Buffer to collect adjacent thinking tokens
            thinking_buffer = ""
            in_thinking = False
            
            # Stream tokens as they are generated
            last_token_index = 0
            while result_thread.is_alive() or last_token_index < len(tokens):
                # Process any new tokens
                while last_token_index < len(tokens):
                    token, finished = tokens[last_token_index]
                    last_token_index += 1
                    
                    # Handle thinking mode
                    if "<thinking>" in token and not in_thinking:
                        in_thinking = True
                        yield "🤔 Thinking...\n"
                        thinking_buffer = ""
                        continue
                    
                    if "</thinking>" in token and in_thinking:
                        in_thinking = False
                        if thinking_buffer:
                            yield f"```\n{thinking_buffer.strip()}\n```\n"
                            thinking_buffer = ""
                        continue
                    
                    if in_thinking:
                        thinking_buffer += token
                        continue
                    
                    # Normal token
                    if token:
                        yield token
                    
                    # If finished, exit loop
                    if finished:
                        return
                
                # Wait a bit before checking for new tokens
                await asyncio.sleep(0.01)
            
            # Ensure any remaining thinking buffer is output
            if thinking_buffer:
                yield f"```\n{thinking_buffer.strip()}\n```\n"
            
        except Exception as e:
            logger.error(f"Error running LangChain agent async: {str(e)}", exc_info=True)
            yield f"Error: {str(e)}"
    
    async def stream_langchain_reasoning(self, conversation_id: str, query: str) -> AsyncGenerator[str, None]:
        """Stream Chain-of-Thought reasoning from LangChain agent"""
        token_queue = asyncio.Queue()

        async def async_streaming_callback(token, is_done=False):
            await token_queue.put((token, is_done))
        
        # Chạy agent trong thread riêng
        agent_thread = threading.Thread(
            target=self._run_agent_for_streaming,
            args=(conversation_id, query, async_streaming_callback)
        )
        agent_thread.start()
        
        # Đọc tokens từ queue và trả về
        is_done = False
        while not is_done:
            try:
                # Timeout để không block vô hạn
                token, is_done = await asyncio.wait_for(token_queue.get(), timeout=0.1)
                if token:  # Chỉ trả về token có nội dung
                    yield token
                token_queue.task_done()
            except asyncio.TimeoutError:
                # Nếu thread vẫn chạy, đợi thêm
                if agent_thread.is_alive():
                    await asyncio.sleep(0.1)
                else:
                    # Thread đã kết thúc nhưng không có signal is_done
                    is_done = True
                    
        # Đảm bảo thread đã kết thúc
        agent_thread.join(timeout=0.5)

    def _run_agent_for_streaming(self, conversation_id, query, streaming_callback):
        try:
            # Lấy hoặc tạo agent
            agent = self.get_langchain_agent(conversation_id)
            if not agent:
                agent = self.create_langchain_agent(conversation_id, streaming_callback)
            
            # Lấy chat history
            chat_history = []
            if conversation_id in self._langchain_memory:
                memory = self._langchain_memory[conversation_id]
                if hasattr(memory, "chat_memory") and hasattr(memory.chat_memory, "messages"):
                    chat_history = memory.chat_memory.messages
            
            # Tạo một wrapper đồng bộ cho callback bất đồng bộ
            import asyncio
            
            def sync_callback(text, is_done=False):
                """Wrapper đồng bộ cho callback bất đồng bộ"""
                if asyncio.iscoroutinefunction(streaming_callback):
                    # Tạo và chạy một vòng lặp sự kiện mới trong thread này
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(streaming_callback(text, is_done))
                    finally:
                        loop.close()
                else:
                    # Nếu không phải hàm coroutine, gọi trực tiếp
                    streaming_callback(text, is_done)
            
            # Đơn giản hóa - sử dụng invoke thay vì run
            try:
                if hasattr(agent, 'invoke'):
                    # Sử dụng invoke với các tùy chọn đơn giản hơn
                    result = agent.invoke(
                        {"input": query, "chat_history": chat_history}
                    )
                    if isinstance(result, dict) and "output" in result:
                        sync_callback(result["output"], True)
                    else:
                        sync_callback(str(result), True)
                else:
                    # Sử dụng chain để trích xuất kết quả đúng
                    from langchain.chains.llm import LLMChain
                    from langchain.prompts import PromptTemplate
                    
                    # Tạo một chain đơn giản
                    template = "Answer the following question: {question}"
                    prompt = PromptTemplate(template=template, input_variables=["question"])
                    chain = LLMChain(prompt=prompt, llm=self._langchain_model)
                    result = chain.run(question=query)
                    sync_callback(result, True)
            except Exception as e:
                logger.error(f"Error in agent execution: {str(e)}")
                sync_callback(f"Error executing agent: {str(e)}", True)
        except Exception as e:
            logger.error(f"Error in streaming thread: {str(e)}")
            if 'sync_callback' in locals():
                sync_callback(f"Error: {str(e)}", True)
            else:
                # Fallback nếu sync_callback chưa được định nghĩa
                if asyncio.iscoroutinefunction(streaming_callback):
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(streaming_callback(f"Error: {str(e)}", True))
                    finally:
                        loop.close()
                else:
                    streaming_callback(f"Error: {str(e)}", True)
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings from text using MistralInference
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List[List[float]]: Embedding matrix
        """
        try:
            self._ensure_model_loaded()
            
            # Use get_embeddings method from MistralInference
            if hasattr(self.mistral, 'get_embeddings'):
                return self.mistral.get_embeddings(texts)
            else:
                # Fallback to zero embeddings
                return [[0.0] * 768 for _ in range(len(texts))]
        except Exception as e:
            logger.error(f"Error getting embeddings: {str(e)}", exc_info=True)
            # Fallback to zero embeddings
            return [[0.0] * 768 for _ in range(len(texts))]

    def tokenize(self, text: str) -> List[int]:
        """Tokenize text"""
        try:
            self._ensure_model_loaded()
            return self.tokenizer.encode(text)
        except Exception as e:
            logger.error(f"Error tokenizing text: {str(e)}", exc_info=True)
            return []

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            tokens = self.tokenize(text)
            return len(tokens)
        except Exception as e:
            logger.error(f"Error counting tokens: {str(e)}", exc_info=True)
            return 0

    def _get_conversation_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """
        Lấy lịch sử cuộc trò chuyện cho một conversation_id
        
        Args:
            conversation_id: ID của cuộc trò chuyện
            
        Returns:
            List[Dict[str, str]]: Danh sách các tin nhắn với role và content
        """
        try:
            history = []
            
            # Kiểm tra xem conversation có trong LangChain memory không
            if conversation_id in self._langchain_memory:
                memory = self._langchain_memory[conversation_id]
                
                # Trích xuất tin nhắn từ memory
                if hasattr(memory, "chat_memory") and hasattr(memory.chat_memory, "messages"):
                    for msg in memory.chat_memory.messages:
                        # Xử lý cả message từ LangChain mới và cũ
                        if hasattr(msg, "type") and hasattr(msg, "content"):
                            # Định dạng LangChain mới
                            role = msg.type
                            content = msg.content
                        elif hasattr(msg, "role") and hasattr(msg, "content"):
                            # Định dạng LangChain 0.x hoặc các tin nhắn dict
                            role = msg.role
                            content = msg.content
                        else:
                            # Cố gắng chuyển đổi thành dict nếu có thể
                            msg_dict = msg if isinstance(msg, dict) else (
                                msg.to_dict() if hasattr(msg, "to_dict") else vars(msg)
                            )
                            role = msg_dict.get("role", "unknown")
                            content = msg_dict.get("content", "")
                            
                        # Chỉ thêm tin nhắn hợp lệ
                        if content:
                            history.append({
                                "role": role,
                                "content": content
                            })
                            
                # Cách khác nếu truy cập trực tiếp các tin nhắn
                elif hasattr(memory, "messages"):
                    for msg in memory.messages:
                        if isinstance(msg, dict) and "role" in msg and "content" in msg:
                            history.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })
            
            # Tìm kiếm trong agent nếu không có trong memory
            elif conversation_id in self._langchain_agents:
                agent = self._langchain_agents[conversation_id]
                if hasattr(agent, "memory") and hasattr(agent.memory, "chat_memory"):
                    for msg in agent.memory.chat_memory.messages:
                        if hasattr(msg, "type") and hasattr(msg, "content"):
                            history.append({
                                "role": msg.type,
                                "content": msg.content
                            })
            
            # Kiểm tra KV cache nếu đang sử dụng Mistral (không qua LangChain)
            elif hasattr(self, "mistral") and hasattr(self.mistral, "kv_cache"):
                cache = self.mistral.kv_cache.get(conversation_id, {})
                messages = cache.get("messages", [])
                for msg in messages:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        history.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
            
            return history
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}", exc_info=True)
            return []  # Trả về danh sách rỗng nếu có lỗi

    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory usage of model using memory_utils"""
        try:
            # Use memory_utils from ML module for detailed information
            memory_info = check_memory_usage()
            
            # Add model information
            memory_info["model"] = {
                "loaded": self.model_loaded,
                "uptime_minutes": (time.time() - self._start_time) / 60
            }
            
            # Add cache information
            if self.cache:
                memory_info["cache"] = self.cache.get_stats()
                
            return memory_info
        except Exception as e:
            logger.error(f"Error getting memory info: {str(e)}", exc_info=True)
            
            # Fallback to basic info
            basic_info = {
                "loaded": self.model_loaded,
                "uptime_minutes": (time.time() - self._start_time) / 60
            }
            
            # Add GPU memory info if available
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    basic_info[f"gpu_{i}"] = {
                        "allocated_mb": torch.cuda.memory_allocated(i) / (1024 * 1024),
                        "reserved_mb": torch.cuda.memory_reserved(i) / (1024 * 1024),
                        "max_allocated_mb": torch.cuda.max_memory_allocated(i) / (1024 * 1024)
                    }
                    
            return basic_info

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system and model information
        
        Returns:
            Dict: System information
        """
        try:
            # Get memory information
            memory_info = self.get_memory_info()
            
            # Get model config
            model_config = self.config.config.get("model", {})
            model_id = model_config.get("base_model_id", "unknown")
            
            # Get tokenizer information if loaded
            tokenizer_info = {}
            if self.model_loaded:
                try:
                    tokenizer_info = {
                        "vocab_size": len(self.tokenizer.get_vocab()),
                        "pad_token": str(self.tokenizer.pad_token),
                        "eos_token": str(self.tokenizer.eos_token),
                    }
                except:
                    tokenizer_info = {"status": "loaded but info unavailable"}
            
            # Get LangChain information
            langchain_info = {
                "enabled": self._langchain_model is not None,
                "functions_registered": len(self._function_registry),
                "active_agents": len(self._langchain_agents),
                "conversations": list(self._langchain_memory.keys())
            }
            
            return {
                "model": {
                    "id": model_id,
                    "loaded": self.model_loaded,
                    "uptime_minutes": (time.time() - self._start_time) / 60,
                    "tokenizer": tokenizer_info,
                    "config": {k: v for k, v in model_config.items() if k not in ["lora_config"]}
                },
                "system": {
                    "torch_version": torch.__version__,
                    "cuda_available": torch.cuda.is_available(),
                    "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
                    "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
                    "gpu_names": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())] if torch.cuda.is_available() else []
                },
                "memory": memory_info.get("memory", {}),
                "langchain": langchain_info,
                "cache": {
                    "info": self.cache.get_stats() if hasattr(self.cache, "get_stats") else {},
                    "enabled": self.config.config.get("inference", {}).get("cache_enabled", True)
                }
            }
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    def _get_cache_key(self, prompt: str, **kwargs) -> str:
        """Create cache key from prompt and parameters"""
        # Create dict with all parameters to hash
        cache_dict = {
            "prompt": prompt,
            **kwargs
        }
        
        # Convert to JSON string to hash
        cache_str = json.dumps(cache_dict, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear all cache"""
        if self.cache:
            self.cache.clear()
            logger.info("Model service cache cleared")
    
    def clear_conversation(self, conversation_id: str) -> None:
        """Clear conversation history"""
        # Remove LangChain memory and agent
        if conversation_id in self._langchain_memory:
            del self._langchain_memory[conversation_id]
        
        if conversation_id in self._langchain_agents:
            del self._langchain_agents[conversation_id]
        
        logger.info(f"Cleared conversation: {conversation_id}")