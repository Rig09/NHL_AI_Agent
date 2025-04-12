import os
import sys
import pytest
import streamlit as st
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import LLMResult, ChatGeneration, ChatGenerationChunk
from typing import List, Dict, Any

# Get the absolute path to the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the project root to the Python path
sys.path.insert(0, project_root)

@pytest.fixture(autouse=True)
def mock_streamlit_session_state():
    """Mock the Streamlit session state for testing."""
    # Create a mock session_state object
    with patch('streamlit.session_state', create=True) as mock_session_state:
        # Create a dictionary-like object to mimic session_state behavior
        session_dict = {}
        
        # Make mock_session_state behave like a dictionary with the __getitem__ method
        mock_session_state.__getitem__ = lambda _, key: session_dict.get(key)
        
        # Make the mock behave like a dictionary with the __setitem__ method
        mock_session_state.__setitem__ = lambda _, key, value: session_dict.update({key: value})
        
        # Add __contains__ to check if keys exist
        mock_session_state.__contains__ = lambda _, key: key in session_dict
        
        yield mock_session_state

@pytest.fixture
def mock_openai_message():
    """Create a mock message for testing."""
    return HumanMessage(content="Test message")

@pytest.fixture
def mock_openai_generation_response():
    """Create a mock OpenAI chat completion response."""
    message = AIMessage(content="Test response")
    generation = ChatGeneration(message=message)
    return LLMResult(generations=[[generation]])

@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock = MagicMock()
    mock.chat = MagicMock()
    mock.chat.completions = MagicMock()
    mock.chat.completions.create = MagicMock()
    return mock

@pytest.fixture
def mock_embedding_response():
    """Create a mock embedding response."""
    return [0.1, 0.2, 0.3, 0.4, 0.5]

@pytest.fixture
def mock_embeddings_response():
    """Create a mock embeddings response for multiple texts."""
    return [
        [0.1, 0.2, 0.3, 0.4, 0.5],
        [0.2, 0.3, 0.4, 0.5, 0.6],
        [0.3, 0.4, 0.5, 0.6, 0.7]
    ]

@pytest.fixture
def mock_time_series():
    """Create a series of mock timestamps for testing rate limits."""
    now = datetime.now()
    
    # Create a series of timestamps within the last minute
    recent_timestamps = [now - timedelta(seconds=i*5) for i in range(12)]  # 12 calls in the last minute
    
    # Create some older timestamps (outside the 1-minute window)
    older_timestamps = [now - timedelta(seconds=61 + i*5) for i in range(5)]
    
    return recent_timestamps + older_timestamps

@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ['TESTING'] = 'true'
    os.environ['OPENAI_API_KEY'] = 'sk-test-12345'
    os.environ['OPENAI_API_BASE'] = 'http://mock-openai-api'
    os.environ['OPENAI_API_TYPE'] = 'mock' 