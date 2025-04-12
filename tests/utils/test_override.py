"""
Test override module to replace real API calls during tests.
This file is imported by run_tests.sh to provide mock implementations.
"""

import streamlit as st
from typing import Any, List, Callable, Dict, Optional
from langchain_core.outputs import LLMResult, ChatResult, ChatGeneration
from langchain_core.messages import HumanMessage, AIMessage
import unittest.mock

# Mock implementation of SimpleOpenAIThrottler
class MockSimpleOpenAIThrottler:
    def __init__(self, requests_per_minute=60):
        self.requests_per_minute = requests_per_minute
        # Initialize throttle tracking in session state
        if not hasattr(st.session_state, 'openai_throttle'):
            st.session_state.openai_throttle = {"timestamps": []}
    
    def check_rate_limit(self) -> bool:
        # Always allow requests in test mode
        return True
    
    def record_request(self) -> None:
        # No-op for testing
        if "timestamps" not in st.session_state.openai_throttle:
            st.session_state.openai_throttle["timestamps"] = []
        st.session_state.openai_throttle["timestamps"].append("mock_timestamp")
    
    def throttled_call(self, func: Callable, *args, **kwargs) -> Any:
        # For testing, don't actually call the function - return test data
        if func.__name__ == '_original_invoke' or func.__name__ == 'invoke':
            # Return a mock chat response
            return {"output": "This is a mock response from the test implementation."}
        elif func.__name__ == '_original_generate' or func.__name__ == 'generate':
            # Return a mock generation response
            message = AIMessage(content="This is a mock response from the test implementation.")
            generation = ChatGeneration(message=message)
            return LLMResult(generations=[[generation]])
        elif func.__name__ == '_original_embed_query' or func.__name__ == 'embed_query':
            # Return a mock embedding
            return [0.1] * 1536
        elif func.__name__ == '_original_embed_documents' or func.__name__ == 'embed_documents':
            # Return mock embeddings for multiple documents
            return [[0.1] * 1536 for _ in range(len(args[0]))]
        else:
            # For any other function, return None
            return None

# Mock the LangChain OpenAI chat class
class MockChatOpenAI:
    def __init__(self, *args, **kwargs):
        self.model_name = kwargs.get('model', 'gpt-3.5-turbo')
        self.temperature = kwargs.get('temperature', 0.7)
        self.client = unittest.mock.MagicMock()
    
    def invoke(self, messages, *args, **kwargs):
        return {"output": "This is a mock response from the test implementation."}
    
    def generate(self, messages, *args, **kwargs):
        message = AIMessage(content="This is a mock response from the test implementation.")
        generation = ChatGeneration(message=message)
        return LLMResult(generations=[[generation]])

# Mock the LangChain OpenAI embeddings class
class MockOpenAIEmbeddings:
    def __init__(self, *args, **kwargs):
        self.model = kwargs.get('model', 'text-embedding-3-small')
        self.client = unittest.mock.MagicMock()
    
    def embed_query(self, text, *args, **kwargs):
        return [0.1] * 1536
    
    def embed_documents(self, texts, *args, **kwargs):
        return [[0.1] * 1536 for _ in range(len(texts))]

# Module-level function to patch all necessary classes
def patch_throttling():
    """
    Replace the real implementations with mock versions.
    This is called from run_tests.sh before running tests.
    """
    from src.utils.throttling import api_throttler
    import langchain_openai
    import openai
    import unittest.mock
    
    # Replace the real implementation with our mock
    api_throttler.SimpleOpenAIThrottler = MockSimpleOpenAIThrottler
    
    # Apply our mock classes
    langchain_openai.ChatOpenAI = MockChatOpenAI
    langchain_openai.OpenAIEmbeddings = MockOpenAIEmbeddings
    
    # Create a mock OpenAI client
    class MockOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = unittest.mock.MagicMock()
            self.embeddings = unittest.mock.MagicMock()
            self.chat.completions = unittest.mock.MagicMock()
            self.chat.completions.create = self._mock_chat_create
            self.embeddings.create = self._mock_embeddings_create
        
        def _mock_chat_create(self, *args, **kwargs):
            mock_response = unittest.mock.MagicMock()
            mock_response.choices = [unittest.mock.MagicMock()]
            mock_response.choices[0].message.content = "This is a mock response from the test implementation."
            return mock_response
        
        def _mock_embeddings_create(self, *args, **kwargs):
            mock_response = unittest.mock.MagicMock()
            mock_response.data = [unittest.mock.MagicMock()]
            mock_response.data[0].embedding = [0.1] * 1536
            return mock_response
    
    # Patch all OpenAI API calls
    openai.OpenAI = MockOpenAI
    
    # Ensure patching is deeper
    def mock_request(*args, **kwargs):
        raise ValueError("No real API calls should be made during tests")
    
    # Patch at the lowest level to prevent any real API calls
    openai._base_client.BaseClient._request = mock_request
    
    print("OpenAI and LangChain implementations replaced with test versions") 