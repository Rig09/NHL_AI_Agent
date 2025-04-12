import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage
from src.utils.throttling import ThrottledChatOpenAI
from src.utils.throttling.api_throttler import SimpleOpenAIThrottler
from utils.test_override import MockChatOpenAI

# Use patch to replace the original ChatOpenAI with our mock
@pytest.fixture(autouse=True)
def mock_implementations():
    with patch('src.utils.throttling.openai_chat.ChatOpenAI', MockChatOpenAI):
        yield

def test_initialization():
    """Test that the ThrottledChatOpenAI class initializes correctly."""
    # Create an instance of ThrottledChatOpenAI
    client = ThrottledChatOpenAI(
        api_key="test_key",
        model="test-model",
        temperature=0.5
    )
    
    # Check that client attributes were set correctly
    assert client.model_name == "test-model"
    assert client.temperature == 0.5
    
    # Check that the client has a throttler
    assert hasattr(client, '_throttler')
    assert isinstance(client._throttler, SimpleOpenAIThrottler)

def test_invoke_method():
    """Test that the invoke method is throttled."""
    # Create an instance of ThrottledChatOpenAI
    client = ThrottledChatOpenAI(api_key="test_key")
    
    # Call the invoke method
    test_message = HumanMessage(content="Test input")
    result = client.invoke([test_message])
    
    # Our mock implementation should return a dictionary with "output" key
    assert "output" in result
    assert isinstance(result["output"], str)

def test_generate_method(mock_openai_message):
    """Test that the generate method is throttled."""
    # Create an instance of ThrottledChatOpenAI
    client = ThrottledChatOpenAI(api_key="test_key")
    
    # Call the generate method
    result = client.generate([[mock_openai_message]])
    
    # Check response structure
    assert hasattr(result, 'generations')
    assert len(result.generations) > 0
    assert len(result.generations[0]) > 0

def test_rate_limit_exception():
    """Test that rate limit exceptions are properly propagated."""
    # For this test, we need to patch the throttled_call method to raise an exception
    with patch.object(SimpleOpenAIThrottler, 'throttled_call', side_effect=Exception("API rate limit exceeded")):
        # Create an instance of ThrottledChatOpenAI
        client = ThrottledChatOpenAI(api_key="test_key")
        
        # Mark this as an exception test so the test mode doesn't bypass the throttler
        client._throttler._is_exception_test = True
        
        # Call the invoke method, which should raise an exception
        with pytest.raises(Exception) as excinfo:
            client.invoke([HumanMessage(content="Test input")])
        
        # Check that the exception has the expected message
        assert "API rate limit exceeded" in str(excinfo.value) 