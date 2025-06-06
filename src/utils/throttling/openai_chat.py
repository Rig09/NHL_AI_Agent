from langchain_openai import ChatOpenAI
from .api_throttler import SimpleOpenAIThrottler
from typing import Any, Dict, Optional, List
import functools
from pydantic import model_validator, ConfigDict
import os
from langchain_core.outputs import LLMResult, ChatGeneration
from langchain_core.messages import AIMessage

class ThrottledChatOpenAI(ChatOpenAI):
    """
    A simple wrapper around the LangChain ChatOpenAI class that applies basic throttling
    to avoid rate limits.
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, api_key=None, model="gpt-3.5-turbo", temperature=0.7, **kwargs):
        """
        Initialize the throttled OpenAI chat client.
        
        Args:
            api_key: The OpenAI API key
            model: The model name to use
            temperature: Temperature parameter for the model
            **kwargs: Additional kwargs to pass to the ChatOpenAI constructor
        """
        # Initialize the OpenAI client
        super().__init__(
            api_key=api_key,
            model=model,
            temperature=temperature,
            **kwargs
        )
        
        # Create the throttler
        self._throttler = SimpleOpenAIThrottler(requests_per_minute=60)
        
        # Store original methods
        self._original_invoke = super().invoke
        self._original_generate = super().generate
        
        # Create throttled versions of the methods
        self._throttled_invoke = self._create_throttled_invoke()
        self._throttled_generate = self._create_throttled_generate()
    
    def _create_throttled_invoke(self):
        """Create a throttled version of the invoke method"""
        @functools.wraps(self._original_invoke)
        def throttled_invoke(*args, **kwargs):
            return self._throttler.throttled_call(self._original_invoke, *args, **kwargs)
        return throttled_invoke
    
    def _create_throttled_generate(self):
        """Create a throttled version of the generate method"""
        @functools.wraps(self._original_generate)
        def throttled_generate(*args, **kwargs):
            return self._throttler.throttled_call(self._original_generate, *args, **kwargs)
        return throttled_generate
    
    def invoke(self, *args, **kwargs):
        """Override the invoke method with the throttled version"""
        return self._throttled_invoke(*args, **kwargs)
    
    def generate(self, *args, **kwargs):
        """Override the generate method with the throttled version"""
        return self._throttled_generate(*args, **kwargs) 