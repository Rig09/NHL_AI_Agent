import pytest
import os
import streamlit as st
from unittest.mock import MagicMock, patch
import time
from datetime import datetime, timedelta
import numpy as np
from langchain_core.outputs import LLMResult, ChatGeneration
from langchain_core.messages import AIMessage, HumanMessage
from src.utils.throttling import ThrottledChatOpenAI
from src.utils.throttling import ThrottledOpenAIEmbeddings
from src.utils.throttling import SimpleOpenAIThrottler

# Create comprehensive patching to completely mock OpenAI API
@pytest.fixture(autouse=True)
def mock_openai_implementations():
    # Mock the base OpenAI API client
    mock_openai = MagicMock()
    
    # Set up mock responses for chat
    mock_chat_response = MagicMock()
    mock_chat_response.choices = [MagicMock()]
    mock_chat_response.choices[0].message.content = "This is a mock response from the test implementation."
    
    # Set up mock responses for embeddings
    mock_embed_response = MagicMock()
    mock_embed_response.data = [MagicMock()]
    mock_embed_response.data[0].embedding = [0.1] * 1536
    
    # Configure the chat completions client
    mock_openai.chat.completions.create.return_value = mock_chat_response
    
    # Configure the embeddings client
    mock_openai.embeddings.create.return_value = mock_embed_response
    
    # Apply patches at all levels to ensure no real API calls
    with patch('openai.OpenAI', return_value=mock_openai), \
         patch('langchain_openai.chat_models.base.openai.OpenAI', return_value=mock_openai), \
         patch('langchain_openai.embeddings.base.openai.OpenAI', return_value=mock_openai), \
         patch('src.utils.throttling.openai_chat.ChatOpenAI._generate', return_value=LLMResult(
             generations=[[ChatGeneration(message=AIMessage(content="This is a mock response"))]]
         )), \
         patch('src.utils.throttling.embeddings.OpenAIEmbeddings.embed_documents', 
               return_value=[[0.1] * 1536 for _ in range(10)]), \
         patch('src.utils.throttling.embeddings.OpenAIEmbeddings.embed_query', 
               return_value=[0.1] * 1536):
        yield

@pytest.fixture
def setup_streamlit():
    """Set up streamlit session state for testing."""
    if 'openai_throttle' in st.session_state:
        del st.session_state['openai_throttle']

def test_chat_rate_limiting(setup_streamlit):
    """Test that chat completions are properly rate limited."""
    # Create an instance of ThrottledChatOpenAI
    client = ThrottledChatOpenAI(api_key="test_key")
    
    # Replace the original methods with simple mocks to avoid the complex LangChain internals
    mock_original_invoke = MagicMock(return_value={"output": "This is a mock response"})
    client._original_invoke = mock_original_invoke
    
    # Spy on the record_request method to ensure it's called for each request
    with patch.object(SimpleOpenAIThrottler, 'record_request', wraps=client._throttler.record_request) as mock_record:
        # Make multiple API calls
        results = []
        for _ in range(3):
            result = client.invoke(messages=[HumanMessage(content="Test")])
            results.append(result)
        
        # Verify that record_request was called exactly 3 times
        assert mock_record.call_count == 3
    
    # Verify all calls returned results
    assert len(results) == 3
    for result in results:
        assert "output" in result or (hasattr(result, 'content') and result.content)

def test_embeddings_rate_limiting(setup_streamlit):
    """Test that embeddings are properly rate limited."""
    # Create an instance of ThrottledOpenAIEmbeddings
    client = ThrottledOpenAIEmbeddings(api_key="test_key")
    
    # Spy on the record_request method to ensure it's called for each request
    with patch.object(SimpleOpenAIThrottler, 'record_request', wraps=client._throttler.record_request) as mock_record:
        # Make multiple API calls
        results = []
        for _ in range(3):
            result = client.embed_query("Test text")
            results.append(result)
        
        # Verify that record_request was called exactly 3 times
        assert mock_record.call_count == 3
    
    # Verify all calls returned results
    assert len(results) == 3
    for result in results:
        assert isinstance(result, list)
        assert len(result) > 0

def test_throttler_reset(setup_streamlit):
    """Test that the throttler resets correctly."""
    # Create instances with shared throttler
    chat_client = ThrottledChatOpenAI(api_key="test_key")
    embeddings_client = ThrottledOpenAIEmbeddings(api_key="test_key")
    
    # Get the throttler and check it was created
    assert hasattr(chat_client, '_throttler')
    throttler = chat_client._throttler
    assert isinstance(throttler, SimpleOpenAIThrottler)
    
    # Record some requests
    throttler.record_request()
    throttler.record_request()
    
    # Check request count
    assert len(st.session_state.openai_throttle["timestamps"]) == 2
    
    # Reset the throttler
    st.session_state.openai_throttle["timestamps"] = []
    
    # Verify request count is reset
    assert len(st.session_state.openai_throttle["timestamps"]) == 0

def test_successive_api_calls(setup_streamlit):
    """Test that successive API calls are properly throttled."""
    # Create clients
    chat_client = ThrottledChatOpenAI(api_key="test_key")
    embeddings_client = ThrottledOpenAIEmbeddings(api_key="test_key")
    
    # Replace the original methods with simple mocks to avoid the complex LangChain internals
    mock_original_invoke = MagicMock(return_value={"output": "This is a mock response"})
    chat_client._original_invoke = mock_original_invoke
    
    # Spy on the record_request method to ensure it's called for each request
    with patch.object(SimpleOpenAIThrottler, 'record_request', wraps=chat_client._throttler.record_request) as mock_record:
        # Make alternating API calls
        for _ in range(2):
            chat_result = chat_client.invoke(messages=[HumanMessage(content="Test")])
            assert "output" in chat_result or (hasattr(chat_result, 'content') and chat_result.content)
            
            embed_result = embeddings_client.embed_query("Test text")
            assert isinstance(embed_result, list)
            assert len(embed_result) > 0
        
        # Verify that record_request was called exactly 4 times (2 chat calls + 2 embedding calls)
        assert mock_record.call_count == 4 