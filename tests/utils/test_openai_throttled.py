import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage
from src.utils.throttling import ThrottledChatOpenAI

@patch('langchain_openai.ChatOpenAI')
@patch('src.utils.throttling.api_throttler.SimpleOpenAIThrottler')
def test_initialization(mock_throttler_class, mock_chat_class):
    """Test that the ThrottledChatOpenAI class initializes correctly."""
    # Create mock instances
    mock_parent = MagicMock()
    mock_chat_class.return_value = mock_parent
    
    mock_throttler = MagicMock()
    mock_throttler_class.return_value = mock_throttler
    
    # Create an instance of ThrottledChatOpenAI
    client = ThrottledChatOpenAI(
        api_key="test_key",
        model="test-model",
        temperature=0.5
    )
    
    # Check that SimpleOpenAIThrottler was initialized correctly
    mock_throttler_class.assert_called_once_with(requests_per_minute=60)
    
    # Check that client attributes were set correctly
    assert client.model_name == "test-model"
    assert client.temperature == 0.5

@patch('langchain_openai.ChatOpenAI')
@patch('src.utils.throttling.api_throttler.SimpleOpenAIThrottler')
def test_invoke_method(mock_throttler_class, mock_chat_class):
    """Test that the invoke method is throttled."""
    # Create mock instances
    mock_parent = MagicMock()
    mock_chat_class.return_value = mock_parent
    
    mock_throttler = MagicMock()
    mock_throttler_class.return_value = mock_throttler
    
    # Create a mock for the original invoke method
    mock_response = {"output": "Test response"}
    mock_parent.invoke = MagicMock(return_value=mock_response)
    
    # Create an instance of ThrottledChatOpenAI
    client = ThrottledChatOpenAI(api_key="test_key")
    
    # Mock the throttled_call to pass through to original_invoke
    mock_throttler.throttled_call = MagicMock(
        side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)
    )
    
    # Call the invoke method
    test_message = HumanMessage(content="Test input")
    result = client.invoke([test_message])
    
    # Check that throttled_call was called with the right arguments
    mock_throttler.throttled_call.assert_called_once()
    
    # Check that the result was returned correctly
    assert result == mock_response

@patch('langchain_openai.ChatOpenAI')
@patch('src.utils.throttling.api_throttler.SimpleOpenAIThrottler')
def test_generate_method(mock_throttler_class, mock_chat_class, mock_openai_generation_response, mock_openai_message):
    """Test that the generate method is throttled."""
    # Create mock instances
    mock_parent = MagicMock()
    mock_chat_class.return_value = mock_parent
    
    mock_throttler = MagicMock()
    mock_throttler_class.return_value = mock_throttler
    
    # Create a mock for the original generate method
    mock_parent.generate = MagicMock(return_value=mock_openai_generation_response)
    
    # Create an instance of ThrottledChatOpenAI
    client = ThrottledChatOpenAI(api_key="test_key")
    
    # Mock the throttled_call to pass through to original_generate
    mock_throttler.throttled_call = MagicMock(
        side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)
    )
    
    # Call the generate method
    result = client.generate([[mock_openai_message]])
    
    # Check that throttled_call was called with the right arguments
    mock_throttler.throttled_call.assert_called_once()
    
    # Check that the result was returned correctly
    assert result == mock_openai_generation_response

@patch('langchain_openai.ChatOpenAI')
@patch('src.utils.throttling.api_throttler.SimpleOpenAIThrottler')
def test_rate_limit_exception(mock_throttler_class, mock_chat_class):
    """Test that rate limit exceptions are properly propagated."""
    # Create mock instances
    mock_parent = MagicMock()
    mock_chat_class.return_value = mock_parent
    
    mock_throttler = MagicMock()
    mock_throttler.throttled_call.side_effect = Exception("API rate limit exceeded")
    mock_throttler_class.return_value = mock_throttler
    
    # Create an instance of ThrottledChatOpenAI
    client = ThrottledChatOpenAI(api_key="test_key")
    
    # Call the invoke method, which should raise an exception
    with pytest.raises(Exception) as excinfo:
        client.invoke([HumanMessage(content="Test input")])
    
    # Check that the exception has the expected message
    assert "API rate limit exceeded" in str(excinfo.value) 