import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.outputs import LLMResult, ChatGeneration
from src.utils.throttling import ThrottledChatOpenAI
from src.utils.throttling.api_throttler import SimpleOpenAIThrottler

class MockChatOpenAI:
    """Mock implementation of ChatOpenAI for testing"""
    def __init__(self, api_key=None, model=None, temperature=None, **kwargs):
        self.api_key = api_key
        self.model_name = model
        self.temperature = temperature
        
    def invoke(self, *args, **kwargs):
        return {"output": "This is a mock response from the test implementation."}
        
    def generate(self, *args, **kwargs):
        message = AIMessage(content="This is a mock response from the test implementation.")
        generation = ChatGeneration(message=message)
        return LLMResult(generations=[[generation]])

# Set up patches for all necessary components to prevent real API calls
@pytest.fixture(autouse=True)
def mock_implementations():
    # Create a deeper patching setup that prevents any real OpenAI API calls
    with patch('src.utils.throttling.openai_chat.ChatOpenAI', MockChatOpenAI), \
         patch('openai.OpenAI'), \
         patch('langchain_openai.chat_models.base.openai.OpenAI'):
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
    
    # Create a mock for the throttler to verify it's called
    mock_throttler = MagicMock()
    client._throttler = mock_throttler
    mock_throttler.throttled_call.return_value = {"output": "This is a mock response from the test implementation."}
    
    # Call the invoke method
    test_message = HumanMessage(content="Test input")
    result = client.invoke([test_message])
    
    # Verify the throttler was called
    mock_throttler.throttled_call.assert_called_once()
    
    # Check the result
    assert "output" in result
    assert isinstance(result["output"], str)

def test_generate_method():
    """Test that the generate method is throttled."""
    # Create an instance of ThrottledChatOpenAI
    client = ThrottledChatOpenAI(api_key="test_key")
    
    # Create a mock for the throttler to verify it's called
    mock_throttler = MagicMock()
    client._throttler = mock_throttler
    
    # Set up the mock return value
    message = AIMessage(content="This is a mock response from the test implementation.")
    generation = ChatGeneration(message=message)
    mock_response = LLMResult(generations=[[generation]])
    mock_throttler.throttled_call.return_value = mock_response
    
    # Call the generate method
    test_message = HumanMessage(content="Test input")
    result = client.generate([[test_message]])
    
    # Verify the throttler was called
    mock_throttler.throttled_call.assert_called_once()
    
    # Check response structure
    assert hasattr(result, 'generations')
    assert len(result.generations) > 0
    assert len(result.generations[0]) > 0

def test_rate_limit_exception():
    """Test that rate limit exceptions are properly propagated."""
    # Create an instance of ThrottledChatOpenAI
    client = ThrottledChatOpenAI(api_key="test_key")
    
    # Create a mock for the throttler that raises an exception
    mock_throttler = MagicMock()
    client._throttler = mock_throttler
    mock_throttler.throttled_call.side_effect = Exception("API rate limit exceeded")
    
    # Call the invoke method, which should raise an exception
    with pytest.raises(Exception) as excinfo:
        client.invoke([HumanMessage(content="Test input")])
    
    # Check that the exception message contains expected text
    assert "API rate limit exceeded" in str(excinfo.value) 