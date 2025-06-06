import pytest
from unittest.mock import MagicMock, patch
from src.utils.throttling import ThrottledOpenAIEmbeddings
from src.utils.throttling.api_throttler import SimpleOpenAIThrottler

class MockOpenAIEmbeddings:
    """Mock implementation of OpenAIEmbeddings for testing"""
    def __init__(self, api_key=None, model=None, **kwargs):
        self.api_key = api_key
        self.model = model  # Note: using model instead of model_name to match actual class
        
    def embed_documents(self, texts, **kwargs):
        # Return a mock embedding for each text
        return [[0.1] * 1536 for _ in range(len(texts))]
        
    def embed_query(self, text, **kwargs):
        # Return a mock embedding
        return [0.1] * 1536

# Use patch to replace the original OpenAIEmbeddings and prevent any real API calls
@pytest.fixture(autouse=True)
def mock_embeddings_implementation():
    with patch('src.utils.throttling.embeddings.OpenAIEmbeddings', MockOpenAIEmbeddings), \
         patch('openai.OpenAI'), \
         patch('langchain_openai.embeddings.base.openai.OpenAI'):
        yield

def test_initialization():
    """Test that the ThrottledOpenAIEmbeddings class initializes correctly."""
    # Create an instance of ThrottledOpenAIEmbeddings
    embeddings = ThrottledOpenAIEmbeddings(
        api_key="test_key",
        model="test-model"
    )
    
    # Check that embeddings has a throttler
    assert hasattr(embeddings, '_throttler')
    assert isinstance(embeddings._throttler, SimpleOpenAIThrottler)

def test_embed_query_method():
    """Test that the embed_query method is throttled."""
    # Create an instance of ThrottledOpenAIEmbeddings
    embeddings = ThrottledOpenAIEmbeddings(api_key="test_key")
    
    # Create a mock for the throttler to verify it's called
    mock_throttler = MagicMock()
    embeddings._throttler = mock_throttler
    mock_throttler.throttled_call.return_value = [0.1] * 1536
    
    # Call the embed_query method
    result = embeddings.embed_query("Test query")
    
    # Verify the throttler was called
    mock_throttler.throttled_call.assert_called_once()
    
    # Check the result
    assert isinstance(result, list)
    assert len(result) == 1536  # OpenAI embeddings are typically 1536 dimensions
    assert all(isinstance(val, float) for val in result)

def test_embed_documents_method():
    """Test that the embed_documents method is throttled."""
    # Create an instance of ThrottledOpenAIEmbeddings
    embeddings = ThrottledOpenAIEmbeddings(api_key="test_key")
    
    # Create a mock for the throttler to verify it's called
    mock_throttler = MagicMock()
    embeddings._throttler = mock_throttler
    
    # Set up the mock return value
    documents = ["Doc 1", "Doc 2", "Doc 3"]
    mock_embeddings = [[0.1] * 1536 for _ in range(len(documents))]
    mock_throttler.throttled_call.return_value = mock_embeddings
    
    # Call the embed_documents method
    result = embeddings.embed_documents(documents)
    
    # Verify the throttler was called
    mock_throttler.throttled_call.assert_called_once()
    
    # Check the result
    assert isinstance(result, list)
    assert len(result) == len(documents)
    assert all(isinstance(doc_embedding, list) for doc_embedding in result)
    assert all(len(doc_embedding) == 1536 for doc_embedding in result)

def test_rate_limit_exception():
    """Test that rate limit exceptions are properly propagated."""
    # Create an instance of ThrottledOpenAIEmbeddings
    embeddings = ThrottledOpenAIEmbeddings(api_key="test_key")
    
    # Create a mock for the throttler that raises an exception
    mock_throttler = MagicMock()
    embeddings._throttler = mock_throttler
    mock_throttler.throttled_call.side_effect = Exception("API rate limit exceeded")
    
    # Call the embed_query method, which should raise an exception
    with pytest.raises(Exception) as excinfo:
        embeddings.embed_query("Test query")
    
    # Check that the exception message contains expected text
    assert "API rate limit exceeded" in str(excinfo.value) 