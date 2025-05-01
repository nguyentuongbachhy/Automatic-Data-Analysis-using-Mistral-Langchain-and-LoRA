"""
LangChain integration utilities for Mistral model
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional, Callable

from langchain.agents import AgentType, initialize_agent, Tool
from langchain.callbacks.base import BaseCallbackHandler
from langchain.prompts import PromptTemplate
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManager

# PostgreSQL 
import psycopg2
import pandas as pd

# Import from ml modules
from ml.data.data_processor import DataProcessor
from ml.analysis.analyzer import DataAnalyzer

logger = logging.getLogger(__name__)

class MistralLLM(LLM):
    """LangChain compatible LLM using MistralInference"""
    
    mistral_inference = None
    model_name: str = "Mistral"
    temperature: float = 0.7
    max_tokens: int = 2048
    
    def __init__(self, mistral_inference, **kwargs):
        """Initialize with MistralInference instance"""
        super().__init__(**kwargs)
        self.mistral_inference = mistral_inference
        
        # Set parameters if provided
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
            # Pass any streaming callback manager to the mistral generate
            callbacks = None
            if run_manager:
                callbacks = run_manager.get_child()
            
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
            
            # Generate using mistral (without KV cache since we're using LangChain memory)
            response = self.mistral_inference.generate(
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

class ChainOfThoughtCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming Chain of Thought reasoning"""
    
    def __init__(self, streaming_callback: Callable[[str, bool], None]):
        """Initialize with a streaming callback function"""
        self.streaming_callback = streaming_callback
        self.thinking_buffer = ""
        self.in_thinking = False
        
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Run when LLM starts running."""
        pass
    
    def on_llm_new_token(self, token: str, **kwargs):
        """Run on new LLM token."""
        # Check if we're entering thinking mode
        if "<thinking>" in token and not self.in_thinking:
            self.in_thinking = True
            self.thinking_buffer = ""
            self.streaming_callback("🤔 Thinking...\n", False)
            return
            
        # Check if we're exiting thinking mode
        if "</thinking>" in token and self.in_thinking:
            self.in_thinking = False
            # Send the complete thinking buffer
            if self.thinking_buffer:
                self.streaming_callback(f"```\n{self.thinking_buffer}\n```\n", False)
            return
            
        # If in thinking mode, accumulate to buffer
        if self.in_thinking:
            self.thinking_buffer += token
        else:
            # Normal token output
            self.streaming_callback(token, False)
    
    def on_llm_end(self, response, **kwargs):
        """Run when LLM ends running."""
        # Send any remaining buffer and signal completion
        if self.thinking_buffer:
            self.streaming_callback(f"```\n{self.thinking_buffer}\n```\n", False)
            self.thinking_buffer = ""
        
        self.streaming_callback("", True)  # Signal completion
    
    def on_llm_error(self, error, **kwargs):
        """Run when LLM errors."""
        self.streaming_callback(f"\nError: {str(error)}", True)
    
    def on_chain_start(self, serialized, inputs, **kwargs):
        """Run when chain starts running."""
        pass
    
    def on_chain_end(self, outputs, **kwargs):
        """Run when chain ends running."""
        pass
    
    def on_chain_error(self, error, **kwargs):
        """Run when chain errors."""
        self.streaming_callback(f"\nChain Error: {str(error)}", True)
    
    def on_tool_start(self, serialized, input_str, **kwargs):
        """Run when tool starts running."""
        self.streaming_callback(f"\n🔧 Using tool: {serialized['name']}\n", False)
    
    def on_tool_end(self, output, **kwargs):
        """Run when tool ends running."""
        # Format tool output for better readability
        formatted_output = f"\n```\n{output}\n```\n"
        self.streaming_callback(formatted_output, False)
    
    def on_tool_error(self, error, **kwargs):
        """Run when tool errors."""
        self.streaming_callback(f"\nTool Error: {str(error)}", True)
    
    def on_text(self, text, **kwargs):
        """Run on text."""
        if not self.in_thinking:
            self.streaming_callback(text, False)
    
    def on_agent_action(self, action, **kwargs):
        """Run on agent action."""
        tool = action.tool
        tool_input = action.tool_input
        self.streaming_callback(f"\n🔍 Deciding to use: {tool}\nWith input: {tool_input}\n", False)
    
    def on_agent_finish(self, finish, **kwargs):
        """Run on agent end."""
        self.streaming_callback(f"\n✅ Agent finished: {finish.return_values['output']}", False)


class PostgreSQLTool:
    """Tool for interacting with PostgreSQL database"""
    
    def __init__(self, dsn=None):
        """Initialize with database connection string"""
        self.dsn = dsn or "postgresql://ecommerce:ecommerce@localhost:5432/datasense"
    
    def execute_query(self, query: str) -> str:
        """Execute SQL query and return results as string"""
        try:
            # Connect to database
            conn = psycopg2.connect(self.dsn)
            
            # Execute query
            df = pd.read_sql_query(query, conn)
            
            # Close connection
            conn.close()
            
            # Return results
            if len(df) == 0:
                return "No results found."
            
            # Convert to string format (limit rows for large results)
            max_rows = 20
            if len(df) > max_rows:
                result_str = df.head(max_rows).to_string() + f"\n\n[Showing {max_rows} of {len(df)} rows]"
            else:
                result_str = df.to_string()
            
            return result_str
        except Exception as e:
            logger.error(f"Error executing SQL query: {str(e)}")
            return f"Error: {str(e)}"
    
    def describe_tables(self) -> str:
        """Get information about available tables"""
        try:
            # Connect to database
            conn = psycopg2.connect(self.dsn)
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
            logger.error(f"Error describing tables: {str(e)}")
            return f"Error: {str(e)}"

def create_cot_prompt_template() -> PromptTemplate:
    """Create Chain of Thought prompt template"""
    return PromptTemplate(
        input_variables=["input"],
        template="""<system>
You're a data analysis assistant with access to powerful tools.
When analyzing data problems, always:
1. Think step by step
2. Decide what tools you need
3. Use the tools to gather information and process data
4. Provide clear explanations of your findings

When thinking through a problem:
<thinking>
- Break down the problem into manageable parts
- Consider what information you need and which tools to use
- Think about the best way to analyze the data
- Plan how to present your findings
</thinking>
</system>

I'll help you analyze your data step by step. Let me know what you need:
{input}"""
    )

def create_analysis_tools(analyzer: DataAnalyzer = None, data_processor: DataProcessor = None) -> List[Tool]:
    """Create tools for data analysis"""
    tools = []
    
    # PostgreSQL tool
    postgres_tool = PostgreSQLTool()
    tools.append(Tool(
        name="PostgreSQL_Query",
        func=postgres_tool.execute_query,
        description="Execute SQL queries on PostgreSQL database. Use to retrieve data from the database."
    ))
    
    tools.append(Tool(
        name="PostgreSQL_Describe_Tables",
        func=postgres_tool.describe_tables,
        description="Get information about available tables in the database."
    ))
    
    # Data processing tools
    if data_processor:
        def process_data(data_str: str) -> str:
            """Process data using DataProcessor"""
            try:
                # Convert string to DataFrame (assume JSON or CSV)
                if data_str.strip().startswith('[') or data_str.strip().startswith('{'):
                    # JSON format
                    df = pd.read_json(data_str)
                else:
                    # CSV format
                    df = pd.read_csv(pd.StringIO(data_str))
                
                # Process data
                processed_df = data_processor.process(df)
                
                # Return processed data
                return processed_df.to_string()
            except Exception as e:
                return f"Error processing data: {str(e)}"
        
        tools.append(Tool(
            name="Process_Data",
            func=process_data,
            description="Process data using DataProcessor. Cleans, normalizes, and prepares data for analysis."
        ))
    
    # Analysis tools
    if analyzer:
        def analyze_data(data_str: str) -> str:
            """Analyze data using DataAnalyzer"""
            try:
                # Convert string to DataFrame
                if data_str.strip().startswith('[') or data_str.strip().startswith('{'):
                    # JSON format
                    df = pd.read_json(data_str)
                else:
                    # CSV format
                    df = pd.read_csv(pd.StringIO(data_str))
                
                # Analyze data
                analysis_results = analyzer.run_analysis(df)
                
                # Return analysis results
                return json.dumps(analysis_results, indent=2)
            except Exception as e:
                return f"Error analyzing data: {str(e)}"
        
        tools.append(Tool(
            name="Analyze_Data",
            func=analyze_data,
            description="Analyze data using DataAnalyzer. Provides statistical analysis, insights, and recommendations."
        ))
    
    # Python code execution tool
    def execute_python(code: str) -> str:
        """Execute Python code in a safe environment"""
        try:
            # Create a local namespace with common data analysis libraries
            import numpy as np
            import pandas as pd
            import matplotlib.pyplot as plt
            
            local_ns = {
                "np": np,
                "pd": pd,
                "plt": plt,
            }
            
            # Redirect stdout to capture print output
            import io
            from contextlib import redirect_stdout
            
            f = io.StringIO()
            with redirect_stdout(f):
                # Execute code
                exec(code, globals(), local_ns)
            
            # Get stdout and return values from namespace
            output = f.getvalue()
            
            # Check if there's a result variable
            result = local_ns.get("result", None)
            if result is not None:
                if isinstance(result, pd.DataFrame):
                    # Limit DataFrame output for readability
                    if len(result) > 20:
                        df_str = result.head(20).to_string() + f"\n\n[Showing 20 of {len(result)} rows]"
                    else:
                        df_str = result.to_string()
                    output += "\n" + df_str
                else:
                    output += "\nResult: " + str(result)
            
            return output if output else "Code executed successfully (no output)"
        except Exception as e:
            return f"Error executing Python code: {str(e)}"
    
    tools.append(Tool(
        name="Execute_Python",
        func=execute_python,
        description="Execute Python code for data analysis. Use pandas, numpy, etc. to analyze data."
    ))
    
    return tools

def create_mistral_agent(
    mistral_llm,
    tools: List[Tool],
    memory: Optional[ConversationBufferMemory] = None,
    streaming_callback: Optional[Callable] = None
) -> Any:
    """Create a LangChain agent using Mistral LLM"""
    # Create callback manager if streaming is enabled
    callback_manager = None
    if streaming_callback:
        cot_handler = ChainOfThoughtCallbackHandler(streaming_callback)
        callback_manager = CallbackManager([cot_handler])
    
    # Create memory if not provided
    if memory is None:
        chat_history = InMemoryChatMessageHistory()
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, chat_memory=chat_history)
    
    # Initialize agent with tools
    agent = initialize_agent(
        tools,
        mistral_llm,
        agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
        verbose=True,
        memory=memory,
        callback_manager=callback_manager,
        handle_parsing_errors=True
    )
    
    return agent

def format_sql_query(query: str) -> str:
    """Format SQL query for better readability"""
    import sqlparse
    return sqlparse.format(
        query, 
        reindent=True, 
        keyword_case='upper'
    )