"""
Mistral inference engine simplified and integrated with LangChain
"""
import os
import time
import json
import logging
import threading
import asyncio
from typing import Dict, Optional, Any, Union, AsyncGenerator, List, Callable

import torch
from transformers import (
    GenerationConfig,
    TextIteratorStreamer
)

from ml.model.model_manager import ModelManager

# Import LangChain integration utilities
from langchain.agents import Tool

logger = logging.getLogger(__name__)

class MistralInference:
    """
    Inference engine simplified for Mistral model.
    Improved for better integration with LangChain.
    """
    
    def __init__(self, config_path: Optional[Union[str, Dict]] = None):
        """Initialize inference engine"""
        # Load config
        if isinstance(config_path, str) and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
        elif isinstance(config_path, dict):
            self.config_data = config_path
        else:
            self.config_data = {}
            
        # Use model manager to load model
        self.manager = ModelManager.get_instance(self.config_data)
        self.model_container = self.load_model()
        
        # Default inference parameters
        self.config = self.config_data.get("inference", {})
        
        # LangChain config from config
        self.langchain_config = self.config_data.get("langchain", {})
        
        # Cache for results
        self.enable_cache = self.config.get("cache_enabled", True)
        self.cache = {}
        
        # Function registry for tool usage
        self.functions = {}
        
        logger.info("MistralInference initialized with LangChain compatibility")
    
    def load_model(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load model if not already loaded"""
        return self.manager.load_model(force_reload)
    
    def count_tokens(self, text: str) -> int:
        """
        Count number of tokens in text. Useful for LangChain's TokenCountEstimator.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            int: Number of tokens
        """
        if not self.manager.is_model_available:
            self.load_model()
            
        tokenizer = self.model_container["tokenizer"]
        return len(tokenizer.encode(text))
    
    def format_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Format LangChain messages into Mistral prompt format.
        Supports integration with LangChain ChatMessageHistory.
        
        Args:
            messages: List of messages from LangChain, each with 'role' and 'content'
            
        Returns:
            str: Formatted prompt
        """
        formatted_prompt = ""
        
        # Format for Mistral
        for message in messages:
            role = message.get("role", "").lower()
            content = message.get("content", "")
            
            if role == "system":
                formatted_prompt += f"<system>\n{content}\n</system>\n\n"
            elif role == "user" or role == "human":
                formatted_prompt += f"<user>\n{content}\n</user>\n\n"
            elif role == "assistant" or role == "ai":
                formatted_prompt += f"<assistant>\n{content}\n</assistant>\n\n"
            else:
                # If role is unclear, default to user
                formatted_prompt += f"<user>\n{content}\n</user>\n\n"
        
        # Add token for next assistant output
        if not formatted_prompt.endswith("<assistant>\n"):
            formatted_prompt += "<assistant>\n"
        
        return formatted_prompt
    
    def generate(
        self,
        prompt: str,
        conversation_id: Optional[str] = None,
        use_history: bool = False,  # Changed to default False since using LangChain
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        max_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        do_sample: bool = True,
        stop_sequences: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Generate text without KV cache. Uses LangChain for context management.
        
        Args:
            prompt: Prompt or formatted chat history
            conversation_id: Optional ID for conversation (unused with LangChain)
            use_history: Whether to use history (unused with LangChain)
            temperature: Adjust output diversity
            top_p: Nucleus sampling parameter 
            top_k: Top-k sampling parameter
            max_tokens: Maximum tokens to generate
            repetition_penalty: Penalty for repetition
            do_sample: Whether to use sampling
            stop_sequences: Sequences to stop generation
            **kwargs: Additional parameters
            
        Returns:
            str: Generated text
        """
        if not self.manager.is_model_available:
            self.load_model()
            
        model = self.model_container["model"]
        tokenizer = self.model_container["tokenizer"]
        
        # Set default values if not provided
        temperature = temperature or self.config.get("default_temperature", 0.7)
        top_p = top_p or self.config.get("default_top_p", 0.9)
        top_k = top_k or self.config.get("default_top_k", 50)
        max_tokens = max_tokens or self.config.get("default_max_tokens", 2048)
        repetition_penalty = repetition_penalty or self.config.get("repetition_penalty", 1.1)
        
        # Prepare input
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        # Log token info
        input_token_count = len(inputs["input_ids"][0])
        logger.info(f"Input token count: {input_token_count}")
        
        # Generation config
        generation_config = GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_new_tokens=max_tokens,
            repetition_penalty=repetition_penalty,
            do_sample=do_sample,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            **{k: v for k, v in kwargs.items() if k not in ['use_cache']}
        )
        
        # Handle stop sequences
        stopping_criteria = None
        if stop_sequences:
            try:
                from transformers import StoppingCriteria, StoppingCriteriaList
                
                class StopTokensCriteria(StoppingCriteria):
                    def __init__(self, stop_token_ids, start_length):
                        self.stop_token_ids = stop_token_ids
                        self.start_length = start_length
                        
                    def __call__(self, input_ids, scores, **kwargs):
                        # Only check new part of sequence
                        for stop_ids in self.stop_token_ids:
                            if input_ids[0][-len(stop_ids):].tolist() == stop_ids:
                                return True
                        return False
                
                # Convert stop sequences to token ids
                stop_token_ids = [tokenizer.encode(stop_seq)[1:] for stop_seq in stop_sequences]
                stopping_criteria = StoppingCriteriaList([
                    StopTokensCriteria(stop_token_ids, len(inputs["input_ids"][0]))
                ])
                
                # Add stopping criteria to generation_config
                kwargs["stopping_criteria"] = stopping_criteria
                
            except Exception as e:
                logger.warning(f"Failed to set up stopping criteria: {str(e)}")
        
        # Use time.time() instead of torch.cuda.Event
        logger.info(f"Starting generation without KV cache")
        start_time = time.time()
        
        generation_kwargs = {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs.get("attention_mask", None),
            "generation_config": generation_config,
            "return_dict_in_generate": True,
            "output_scores": False,
        }

        # Only add use_cache if not already in kwargs
        if 'use_cache' not in kwargs:
            generation_kwargs["use_cache"] = True

        try:
            # Ensure CUDA cache is freed before generation
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            with torch.no_grad():
                # Simple generation without KV cache
                generation_output = model.generate(**{**generation_kwargs, **kwargs})
                
        except Exception as e:
            logger.error(f"Error during generation: {str(e)}")
            try:
                # Fallback: Try with simpler parameters
                logger.info("Falling back to generation with simpler parameters")
                
                # Ensure CUDA cache is freed
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                # Try with simpler parameters
                simpler_generation_config = GenerationConfig(
                    temperature=0.9,
                    top_p=0.95,
                    top_k=40,
                    max_new_tokens=512,  # Reduce to save memory
                    repetition_penalty=1.0,
                    do_sample=True,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id
                )
                
                with torch.no_grad():
                    generation_output = model.generate(
                        input_ids=inputs["input_ids"],
                        attention_mask=inputs.get("attention_mask", None),
                        generation_config=simpler_generation_config,
                        return_dict_in_generate=True,
                        output_scores=False,
                        use_cache=True,
                    )
            except Exception as fallback_e:
                logger.error(f"Fallback generation also failed: {str(fallback_e)}")
                raise e  # Re-raise original error if fallback fails
        
        # Calculate time using time.time()
        inference_time = time.time() - start_time
        
        # Decode output
        decoded_output = tokenizer.decode(
            generation_output.sequences[0], skip_special_tokens=True
        )
        
        # Count tokens
        output_token_count = len(generation_output.sequences[0]) - input_token_count
        tokens_per_second = output_token_count / inference_time if inference_time > 0 else 0
        
        logger.info(f"Generation completed in {inference_time:.2f}s")
        logger.info(f"Output token count: {output_token_count}")
        logger.info(f"Generation speed: {tokens_per_second:.2f} tokens/second")
        
        # Extract only the assistant's response
        if "</assistant>" in decoded_output:
            response = decoded_output.split("<assistant>")[-1].split("</assistant>")[0].strip()
        else:
            # If no </assistant> tag, extract everything after the prompt
            response = decoded_output[len(prompt):].strip()
        
        return response
    
    def generate_with_langchain_messages(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Generate text from LangChain formatted messages.
        New method for better integration with LangChain and chat tasks.
        
        Args:
            messages: List of messages in LangChain format
            **kwargs: Other parameters for generate()
            
        Returns:
            str: Assistant's response
        """
        # Format messages into Mistral prompt
        prompt = self.format_prompt(messages)
        
        # Generate response
        return self.generate(
            prompt=prompt,
            use_history=False,  # Don't use Mistral's internal history
            **kwargs
        )
    
    async def stream(
        self,
        prompt: str,
        conversation_id: Optional[str] = None,
        use_history: bool = False,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        max_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        do_sample: bool = True,
        stop_sequences: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream output tokens"""
        if not isinstance(prompt, str) or not prompt.strip():
            logger.error(f"Invalid prompt: {type(prompt)}")
            yield "Error: Invalid prompt provided"
            return
        
        if not self.manager.is_model_available:
            self.load_model()
        
        # Get model and tokenizer
        model = self.model_container["model"]
        tokenizer = self.model_container["tokenizer"]
        
        # Set default values if not provided
        temperature = temperature or self.config.get("default_temperature", 0.7)
        top_p = top_p or self.config.get("default_top_p", 0.9)
        top_k = top_k or self.config.get("default_top_k", 50)
        max_tokens = max_tokens or self.config.get("default_max_tokens", 2048)
        repetition_penalty = repetition_penalty or self.config.get("repetition_penalty", 1.1)
        
        try:
            # Prepare input
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            
            # Log token info
            input_token_count = len(inputs["input_ids"][0])
            logger.info(f"Streaming: Input token count: {input_token_count}")
            
            # Handle stop sequences
            stopping_criteria = None
            if stop_sequences:
                try:
                    from transformers import StoppingCriteria, StoppingCriteriaList
                    
                    class StopTokensCriteria(StoppingCriteria):
                        def __init__(self, stop_token_ids, start_length):
                            self.stop_token_ids = stop_token_ids
                            self.start_length = start_length
                            
                        def __call__(self, input_ids, scores, **kwargs):
                            # Only check new part of sequence
                            for stop_ids in self.stop_token_ids:
                                if input_ids[0][-len(stop_ids):].tolist() == stop_ids:
                                    return True
                            return False
                    
                    # Convert stop sequences to token ids
                    stop_token_ids = [tokenizer.encode(stop_seq)[1:] for stop_seq in stop_sequences]
                    stopping_criteria = StoppingCriteriaList([
                        StopTokensCriteria(stop_token_ids, len(inputs["input_ids"][0]))
                    ])
                    
                    # Add stopping criteria to kwargs
                    kwargs["stopping_criteria"] = stopping_criteria
                    
                except Exception as e:
                    logger.warning(f"Failed to set up stopping criteria for streaming: {str(e)}")
            
            # Generation config
            generation_config = GenerationConfig(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_new_tokens=max_tokens,
                repetition_penalty=repetition_penalty,
                do_sample=do_sample,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                **kwargs
            )
            
            # Set up streamer
            streamer = TextIteratorStreamer(
                tokenizer, skip_prompt=True, skip_special_tokens=True
            )
            
            # Generate in a separate thread
            generation_kwargs = {
                "input_ids": inputs["input_ids"],
                "attention_mask": inputs.get("attention_mask", None),
                "generation_config": generation_config,
                "streamer": streamer,
                "use_cache": True  # Use internal cache for this single generation
            }
            
            thread = threading.Thread(target=self._generate_with_streamer, 
                                    kwargs=generation_kwargs)
            thread.start()

            logger.info(f"Streaming generation started")
            
            # Process and yield tokens
            collected_output = ""
            
            for token in streamer:
                collected_output += token
                
                # Don't yield empty tokens
                if not token.strip():
                    continue
                
                # Thêm dòng này để flush ngay lập tức
                yield token
                
                # Thêm một sleep nhỏ để đảm bảo event loop được xử lý
                await asyncio.sleep(0)
            
            # Log completed stream information
            logger.info(f"Streaming completed")
            
            thread.join()
        except Exception as e:
            logger.error(f"Error during streaming: {str(e)}", exc_info=True)
            yield f"Error generating response: {str(e)}"
    
    async def stream_with_langchain_messages(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream text from LangChain formatted messages.
        
        Args:
            messages: List of messages in LangChain format
            **kwargs: Other parameters for stream()
            
        Returns:
            AsyncGenerator[str, None]: Generator yielding tokens
        """
        # Format messages into Mistral prompt
        prompt = self.format_prompt(messages)
        
        # Stream response
        async for token in self.stream(
            prompt=prompt,
            use_history=False,  # Don't use Mistral's internal history
            **kwargs
        ):
            yield token
    
    def _generate_with_streamer(self, **kwargs):
        try:
            model = self.model_container["model"]
            streamer = kwargs.pop("streamer", None)
            input_ids = kwargs.pop("input_ids", None)
            
            # Create generation kwargs without duplicate use_cache
            generation_kwargs = {
                "input_ids": input_ids,
                "streamer": streamer,
            }
            
            # Only add use_cache if it's not already in kwargs
            if 'use_cache' not in kwargs:
                generation_kwargs["use_cache"] = True
                
            try:
                with torch.no_grad():
                    # Generate with merged parameters
                    model.generate(**{**kwargs, **generation_kwargs})
                    
            except Exception as e:
                logger.error(f"Error in streaming generation: {str(e)}")
                if streamer and hasattr(streamer, "add_token"):
                    try:
                        streamer.add_token(f"\n\nError generating response: {str(e)}")
                        streamer.end()
                    except:
                        pass  # Ignore errors in error handling
        except Exception as e:
            logger.error(f"Error in generation thread: {str(e)}")
            # Let the streamer know there was an error
            if streamer and hasattr(streamer, "add_token"):
                try:
                    streamer.add_token(f"\n\nError generating response: {str(e)}")
                    streamer.end()
                except:
                    pass  # Ignore errors in error handling
    
    # Function calling capabilities
    def register_function(self, name: str, func: Callable, description: str, parameters: Dict = None) -> None:
        """
        Register a function that can be called by the model
        
        Args:
            name: Function name
            func: Function to call
            description: Function description
            parameters: Function parameters schema
        """
        self.functions[name] = {
            "function": func,
            "description": description,
            "parameters": parameters or {}
        }
        logger.info(f"Registered function: {name}")
    
    def call_function(self, name: str, **kwargs) -> Any:
        """
        Call a registered function
        
        Args:
            name: Function name
            **kwargs: Function arguments
            
        Returns:
            Any: Function result
        """
        if name not in self.functions:
            raise ValueError(f"Function {name} not registered")
        
        func_info = self.functions[name]
        func = func_info["function"]
        
        return func(**kwargs)
    
    def parse_function_calls(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse function calls from generated text
        
        Args:
            text: Generated text
            
        Returns:
            List[Dict[str, Any]]: List of function calls
        """
        function_calls = []
        
        # Simple regex-based parsing
        import re
        pattern = r'call_function\(([^)]+)\)'
        matches = re.finditer(pattern, text)
        
        for match in matches:
            try:
                args_str = match.group(1)
                # Parse arguments
                args_dict = {}
                for arg in args_str.split(','):
                    if '=' in arg:
                        key, value = arg.split('=', 1)
                        args_dict[key.strip()] = value.strip().strip('"\'')
                
                if 'name' in args_dict:
                    function_name = args_dict.pop('name')
                    function_calls.append({
                        "name": function_name,
                        "arguments": args_dict
                    })
            except Exception as e:
                logger.error(f"Error parsing function call: {str(e)}")
        
        return function_calls
    
    def create_langchain_tools(self) -> List[Tool]:
        """
        Create LangChain tools from registered functions
        
        Returns:
            List[Tool]: List of LangChain tools
        """
        from langchain.agents import Tool
        
        tools = []
        for name, func_info in self.functions.items():
            tools.append(Tool(
                name=name,
                func=func_info["function"],
                description=func_info["description"]
            ))
        
        return tools
    
    def get_token_estimator(self) -> Callable[[str], int]:
        """
        Return function to estimate tokens.
        Needed for LangChain.
        
        Returns:
            Callable: Token estimation function
        """
        return self.count_tokens