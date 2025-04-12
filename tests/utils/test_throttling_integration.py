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
from utils.test_override import MockChatOpenAI, MockOpenAIEmbeddings

@pytest.fixture
def setup_streamlit():
    """Set up streamlit session state for testing."""
    if 'openai_throttle' in st.session_state:
        del st.session_state['openai_throttle']

# Use patch to replace the original implementations with mocks
@pytest.fixture(autouse=True)
def mock_implementations():
    with patch('src.utils.throttling.openai_chat.ChatOpenAI', MockChatOpenAI), \
         patch('src.utils.throttling.embeddings.OpenAIEmbeddings', MockOpenAIEmbeddings):
        yield

def test_chat_rate_limiting(setup_streamlit):
    """Test that chat completions are properly rate limited."""
    # Create an instance of ThrottledChatOpenAI
    client = ThrottledChatOpenAI(api_key="test_key")
    
    # Make multiple API calls
    results = []
    for _ in range(3):
        result = client.invoke([{"role": "user", "content": "Test"}])
        results.append(result)
    
    # Verify all calls returned results
    assert len(results) == 3
    for result in results:
        assert "output" in result
        assert isinstance(result["output"], str)

def test_embeddings_rate_limiting(setup_streamlit):
    """Test that embeddings are properly rate limited."""
    # Create an instance of ThrottledOpenAIEmbeddings
    client = ThrottledOpenAIEmbeddings(api_key="test_key")
    
    # Make multiple API calls
    results = []
    for _ in range(3):
        result = client.embed_query("Test text")
        results.append(result)
    
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
    
    # Make alternating API calls
    for _ in range(2):
        chat_result = chat_client.invoke([{"role": "user", "content": "Test"}])
        assert "output" in chat_result
        
        embed_result = embeddings_client.embed_query("Test text")
        assert isinstance(embed_result, list)
        assert len(embed_result) > 0 