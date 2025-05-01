"""
Factory to create LangChain agents with tool integration for data analysis
"""
import logging
from typing import Dict, List, Any, Optional, Union, Callable

from langchain.agents import AgentType, initialize_agent, AgentExecutor
from langchain.chains.llm import LLMChain
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chat_models.base import BaseChatModel
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.tools import BaseTool, Tool

# Import custom components
from ml.tools.postgres_connector import PostgreSQLConnector, PostgreSQLQueryTool, PostgreSQLSchemaTool, PostgreSQLSampleTool
from ml.tools.data_analysis_tools import DataAnalysisTools

logger = logging.getLogger(__name__)

class ChainOfThoughtCallbackHandler(BaseCallbackHandler):
    """Callback handler for Chain-of-Thought reasoning"""
    
    def __init__(self, streaming_callback: Callable[[str, bool], None]):
        """Initialize with streaming callback"""
        super().__init__()
        self.streaming_callback = streaming_callback
        self.thinking_buffer = ""
        self.in_thinking = False
        self.chunks_since_last_yield = 0
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Run when LLM starts"""
        pass
    
    def on_llm_new_token(self, token: str, **kwargs):
        """Process new token from LLM"""
        # Check for thinking mode start
        if "<thinking>" in token and not self.in_thinking:
            self.in_thinking = True
            self.thinking_buffer = ""
            self.streaming_callback("🤔 Thinking...\n", False)
            return
        
        # Check for thinking mode end
        if "</thinking>" in token and self.in_thinking:
            self.in_thinking = False
            # Send thinking buffer
            if self.thinking_buffer:
                self.streaming_callback(f"```\n{self.thinking_buffer}\n```\n", False)
                self.thinking_buffer = ""
            return
        
        # Accumulate thinking or stream token
        if self.in_thinking:
            self.thinking_buffer += token
            # Periodically send thinking updates for long chains
            self.chunks_since_last_yield += 1
            if self.chunks_since_last_yield >= 50:  # After ~50 chunks, yield update
                self.streaming_callback(f"```\n{self.thinking_buffer}\n```\n", False)
                self.thinking_buffer = ""
                self.chunks_since_last_yield = 0
        else:
            # Stream normal token
            self.streaming_callback(token, False)
    
    def on_llm_end(self, response, **kwargs):
        """Run when LLM ends"""
        # Send any remaining thinking buffer
        if self.thinking_buffer:
            self.streaming_callback(f"```\n{self.thinking_buffer}\n```\n", False)
            self.thinking_buffer = ""
        
        # Signal completion
        self.streaming_callback("", True)
    
    def on_llm_error(self, error, **kwargs):
        """Handle LLM errors"""
        error_msg = f"Error during generation: {str(error)}"
        self.streaming_callback(f"\n❌ {error_msg}", True)
    
    def on_tool_start(self, serialized, input_str, **kwargs):
        """Run when tool execution starts"""
        self.streaming_callback(f"\n🔧 Using tool: {serialized['name']}\nInput: {input_str}\n", False)
    
    def on_tool_end(self, output, **kwargs):
        """Run when tool execution ends"""
        # Format tool output for better readability
        if len(output) > 500:
            short_output = output[:500] + "...[output truncated]"
            formatted_output = f"\n```\n{short_output}\n```\n"
        else:
            formatted_output = f"\n```\n{output}\n```\n"
        
        self.streaming_callback(formatted_output, False)
    
    def on_tool_error(self, error, **kwargs):
        """Handle tool errors"""
        error_msg = f"Tool execution error: {str(error)}"
        self.streaming_callback(f"\n❌ {error_msg}", False)
    
    def on_agent_action(self, action, **kwargs):
        """Run when agent selects an action"""
        self.streaming_callback(f"\n🔍 Deciding to use tool: {action.tool}\nWith input: {action.tool_input}\n", False)
    
    def on_agent_finish(self, finish, **kwargs):
        """Run when agent finishes execution"""
        output = finish.return_values.get("output", "Task completed")
        self.streaming_callback(f"\n✅ {output}", False)

class LangChainAgentFactory:
    """Factory for creating LangChain agents with integrated tools"""
    
    def __init__(
        self,
        llm: Optional[Union[BaseChatModel, Any]] = None,
        db_connection_string: Optional[str] = None,
        agent_type: str = "chat-conversational-react-description"
    ):
        """
        Initialize agent factory
        
        Args:
            llm: LangChain compatible LLM
            db_connection_string: PostgreSQL connection string
            agent_type: Type of agent to create
        """
        self.llm = llm
        self.db_connection_string = db_connection_string
        self.agent_type = self._parse_agent_type(agent_type)
        
        # Initialize components
        self.db_connector = PostgreSQLConnector(db_connection_string)
        self.analysis_tools = DataAnalysisTools(db_connection_string)
        
        # Tools registry
        self._tools = []
        self._register_default_tools()
        
        logger.info("LangChainAgentFactory initialized")
    
    def _parse_agent_type(self, agent_type: str) -> AgentType:
        """
        Parse agent type string to AgentType
        
        Args:
            agent_type: Agent type string
            
        Returns:
            AgentType: LangChain AgentType
        """
        agent_type = agent_type.lower()
        
        if agent_type in ["zero-shot", "zero-shot-react-description"]:
            return AgentType.ZERO_SHOT_REACT_DESCRIPTION
        elif agent_type in ["react", "react-docstore"]:
            return AgentType.REACT_DOCSTORE
        elif agent_type in ["self-ask", "self-ask-with-search"]:
            return AgentType.SELF_ASK_WITH_SEARCH
        elif agent_type in ["conversational", "conversational-react-description"]:
            return AgentType.CONVERSATIONAL_REACT_DESCRIPTION
        elif agent_type in ["chat", "chat-zero-shot", "chat-zero-shot-react-description"]:
            return AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION
        elif agent_type in ["chat-conversational", "chat-conversational-react-description"]:
            return AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION
        elif agent_type in ["openai-functions", "openai-multi-functions"]:
            return AgentType.OPENAI_MULTI_FUNCTIONS
        elif agent_type in ["openai-tools", "openai-multi-tools"]:
            return AgentType.OPENAI_FUNCTIONS
        else:
            logger.warning(f"Unknown agent type '{agent_type}', defaulting to CHAT_CONVERSATIONAL_REACT_DESCRIPTION")
            return AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION
    
    def _register_default_tools(self):
        """Register default tools for data analysis"""
        # PostgreSQL tools
        self._tools.append(PostgreSQLQueryTool(self.db_connector))
        self._tools.append(PostgreSQLSchemaTool(self.db_connector))
        self._tools.append(PostgreSQLSampleTool(self.db_connector))
        
        # Data analysis tools
        self._tools.append(Tool(
            name="process_data",
            func=self.analysis_tools.process_data,
            description="Process and clean data using various techniques. Input can be a DataFrame or path to data file."
        ))
        
        self._tools.append(Tool(
            name="validate_data",
            func=self.analysis_tools.validate_data,
            description="Validate data quality and identify issues. Input can be a DataFrame or path to data file."
        ))
        
        self._tools.append(Tool(
            name="analyze_data",
            func=self.analysis_tools.analyze_data,
            description="Perform comprehensive data analysis. Input should be a DataFrame or path to data file and optional analysis type."
        ))
        
        self._tools.append(Tool(
            name="generate_visualizations",
            func=self.analysis_tools.generate_visualizations,
            description="Generate visualizations from data. Input should be a DataFrame or path to data file, optional columns and chart type."
        ))
        
        self._tools.append(Tool(
            name="generate_insights",
            func=self.analysis_tools.generate_insights,
            description="Generate insights from data. Input should be a DataFrame or path to data file and optional insight types."
        ))
        
        self._tools.append(Tool(
            name="recommend_charts",
            func=self.analysis_tools.recommend_charts,
            description="Recommend chart types for data visualization. Input should be a DataFrame or path to data file and optional columns."
        ))
        
        logger.info(f"Registered {len(self._tools)} default tools")
    
    def register_tool(self, tool: BaseTool):
        """
        Register a custom tool
        
        Args:
            tool: LangChain BaseTool
        """
        self._tools.append(tool)
        logger.info(f"Registered custom tool: {tool.name}")
    
    def create_agent(
        self,
        memory: Optional[ConversationBufferMemory] = None,
        system_message: Optional[str] = None,
        streaming_callback: Optional[Callable[[str, bool], None]] = None,
        verbose: bool = True
    ) -> AgentExecutor:
        """
        Create a LangChain agent
        
        Args:
            memory: ConversationBufferMemory
            system_message: System message for the agent
            streaming_callback: Callback for streaming output
            verbose: Whether to enable verbose output
            
        Returns:
            AgentExecutor: LangChain agent executor
        """
        if self.llm is None:
            raise ValueError("LLM must be provided to create an agent")
        
        # Create memory if not provided
        if memory is None:
            memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        
        # Set up callbacks
        callbacks = []
        if streaming_callback:
            callbacks.append(ChainOfThoughtCallbackHandler(streaming_callback))
        elif verbose:
            callbacks.append(StreamingStdOutCallbackHandler())
        
        callback_manager = CallbackManager(callbacks) if callbacks else None
        
        # Create agent
        agent = initialize_agent(
            self._tools,
            self.llm,
            agent=self.agent_type,
            verbose=verbose,
            memory=memory,
            callback_manager=callback_manager,
            handle_parsing_errors=True
        )
        
        # Customize agent with system message if provided
        if system_message and hasattr(agent, 'agent') and hasattr(agent.agent, 'create_prompt'):
            try:
                # Try to update the system message in the prompt
                system_message = system_message.strip()
                if not system_message.endswith("\n"):
                    system_message += "\n"
                
                # Customize prompt template
                new_prompt = agent.agent.create_prompt(
                    system_message=system_message,
                    tools=self._tools
                )
                
                agent.agent.prompt = new_prompt
                logger.info("Updated agent with custom system message")
            except Exception as e:
                logger.warning(f"Failed to set system message: {str(e)}")
        
        return agent
    
    def get_tools(self) -> List[BaseTool]:
        """
        Get all registered tools
        
        Returns:
            List[BaseTool]: List of tools
        """
        return self._tools.copy()
    
    def create_chain_of_thought_prompt(self) -> PromptTemplate:
        """
        Create a prompt template for Chain-of-Thought reasoning
        
        Returns:
            PromptTemplate: Prompt template
        """
        template = """
        You are a data analysis assistant with access to powerful tools.
        When analyzing data problems, always use the following process:
        
        <thinking>
        1. Break down the problem into steps
        2. Identify what information you need
        3. Determine which tools to use
        4. Plan your analysis approach
        5. Interpret the results
        </thinking>
        
        Use the available tools to help you analyze data and answer questions.
        
        Here's what you need to understand:
        {context}
        
        Question: {question}
        
        Let's work through this step by step:
        """
        
        return PromptTemplate(
            input_variables=["context", "question"],
            template=template.strip()
        )
    
    def create_analysis_chain(
        self,
        prompt_template: Optional[PromptTemplate] = None,
        streaming_callback: Optional[Callable[[str, bool], None]] = None
    ) -> LLMChain:
        """
        Create a Chain-of-Thought analysis chain
        
        Args:
            prompt_template: Custom prompt template
            streaming_callback: Callback for streaming output
            
        Returns:
            LLMChain: Analysis chain
        """
        if self.llm is None:
            raise ValueError("LLM must be provided to create a chain")
        
        # Use default prompt if not provided
        if prompt_template is None:
            prompt_template = self.create_chain_of_thought_prompt()
        
        # Set up callbacks
        callbacks = []
        if streaming_callback:
            callbacks.append(ChainOfThoughtCallbackHandler(streaming_callback))
        
        callback_manager = CallbackManager(callbacks) if callbacks else None
        
        # Create chain
        chain = LLMChain(
            llm=self.llm,
            prompt=prompt_template,
            callback_manager=callback_manager,
            verbose=True
        )
        
        return chain