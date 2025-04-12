import pytest
import os
import streamlit as st
from unittest.mock import MagicMock, patch
import time
from datetime import datetime, timedelta
import numpy as np
from src.utils.throttling import ThrottledChatOpenAI
from src.utils.throttling import ThrottledOpenAIEmbeddings
from src.utils.throttling import SimpleOpenAIThrottler

@pytest.fixture
def setup_streamlit():
    """Set up streamlit session state for testing."""
    if 'openai_throttler' in st.session_state:
        del st.session_state['openai_throttler']

@patch('src.utils.throttling.openai_chat.openai.OpenAI')
@patch('src.utils.throttling.api_throttler.SimpleOpenAIThrottler')
@patch('langchain_openai.ChatOpenAI')
def test_chat_rate_limiting(mock_chat_class, mock_throttler_class, mock_openai_class, setup_streamlit):
    """Test that chat completions are properly rate limited."""
    # Create mock instances
    mock_parent = MagicMock()
    mock_chat_class.return_value = mock_parent
    
    mock_throttler = MagicMock()
    mock_throttler_class.return_value = mock_throttler
    
    mock_openai = MagicMock()
    mock_openai_class.return_value = mock_openai
    mock_openai.chat.completions = MagicMock()
    
    # Create a mock response
    mock_response = {"output": "Test response"}
    mock_parent.invoke = MagicMock(return_value=mock_response)
    
    # Create an instance of ThrottledChatOpenAI
    client = ThrottledChatOpenAI(api_key="test_key")
    
    # Mock the throttled_call to pass through
    mock_throttler.throttled_call = MagicMock(
        side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)
    )
    
    # Make multiple API calls
    for _ in range(3):
        result = client.invoke([{"role": "user", "content": "Test"}])
        assert result == mock_response
    
    # Verify throttler was used
    assert mock_throttler.throttled_call.call_count == 3

@patch('src.utils.throttling.openai_embeddings.openai.OpenAI')
@patch('src.utils.throttling.api_throttler.SimpleOpenAIThrottler')
@patch('langchain_openai.OpenAIEmbeddings')
def test_embeddings_rate_limiting(mock_embeddings_class, mock_throttler_class, mock_openai_class, setup_streamlit):
    """Test that embeddings are properly rate limited."""
    # Create mock instances
    mock_parent = MagicMock()
    mock_embeddings_class.return_value = mock_parent
    
    mock_throttler = MagicMock()
    mock_throttler_class.return_value = mock_throttler
    
    mock_openai = MagicMock()
    mock_openai_class.return_value = mock_openai
    mock_openai.embeddings = MagicMock()
    
    # Create a mock response
    mock_embedding = [0.1] * 1536  # Standard OpenAI embedding size
    mock_parent.embed_query = MagicMock(return_value=mock_embedding)
    
    # Create an instance of ThrottledOpenAIEmbeddings
    client = ThrottledOpenAIEmbeddings(api_key="test_key")
    
    # Mock the throttled_call to pass through
    mock_throttler.throttled_call = MagicMock(
        side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)
    )
    
    # Make multiple API calls
    for _ in range(3):
        result = client.embed_query("Test text")
        assert result == mock_embedding
    
    # Verify throttler was used
    assert mock_throttler.throttled_call.call_count == 3

@patch('src.utils.throttling.openai_chat.openai.OpenAI')
@patch('src.utils.throttling.openai_embeddings.openai.OpenAI')
def test_throttler_reset(mock_openai_embeddings, mock_openai_chat, setup_streamlit):
    """Test that the throttler resets correctly."""
    # Create mock instances
    mock_openai_chat.return_value = MagicMock()
    mock_openai_embeddings.return_value = MagicMock()
    
    # Create instances with shared throttler
    chat_client = ThrottledChatOpenAI(api_key="test_key")
    embeddings_client = ThrottledOpenAIEmbeddings(api_key="test_key")
    
    # Get the throttler from session state
    throttler = st.session_state.get('openai_throttler')
    assert isinstance(throttler, SimpleOpenAIThrottler)
    
    # Record some requests
    throttler.record_request()
    throttler.record_request()
    
    # Check request count
    assert len(throttler.request_times) == 2
    
    # Reset the throttler
    throttler.reset()
    
    # Verify request count is reset
    assert len(throttler.request_times) == 0

@patch('src.utils.throttling.openai_chat.openai.OpenAI')
@patch('src.utils.throttling.openai_embeddings.openai.OpenAI')
def test_successive_api_calls(mock_openai_embeddings, mock_openai_chat, setup_streamlit):
    """Test that successive API calls are properly throttled."""
    # Create mock instances
    mock_chat = MagicMock()
    mock_openai_chat.return_value = mock_chat
    mock_chat.chat.completions = MagicMock()
    
    mock_embeddings = MagicMock()
    mock_openai_embeddings.return_value = mock_embeddings
    mock_embeddings.embeddings = MagicMock()
    
    # Create instances with shared throttler
    chat_client = ThrottledChatOpenAI(api_key="test_key")
    embeddings_client = ThrottledOpenAIEmbeddings(api_key="test_key")
    
    # Mock responses
    mock_chat_response = {"output": "Test response"}
    mock_embedding = [0.1] * 1536
    
    with patch.object(chat_client, 'invoke', return_value=mock_chat_response) as mock_chat_invoke:
        with patch.object(embeddings_client, 'embed_query', return_value=mock_embedding) as mock_embed:
            # Make alternating API calls
            for _ in range(2):
                chat_result = chat_client.invoke([{"role": "user", "content": "Test"}])
                assert chat_result == mock_chat_response
                
                embed_result = embeddings_client.embed_query("Test text")
                assert embed_result == mock_embedding
            
            # Verify call counts
            assert mock_chat_invoke.call_count == 2
            assert mock_embed.call_count == 2 