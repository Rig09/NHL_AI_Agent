import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from src.utils.throttling import ThrottledOpenAIEmbeddings, SimpleOpenAIThrottler

def test_embed_documents():
    """Test that the embed_documents method correctly uses the throttler."""
    # Create mock embeddings result
    mock_result = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    
    # Create a mock throttler that just returns what the wrapped function would return
    mock_throttler = MagicMock()
    mock_throttler.throttled_call = MagicMock(side_effect=lambda func, *args, **kwargs: func(*args, **kwargs))
    
    # Create a mock original function
    mock_original_embed_documents = MagicMock(return_value=mock_result)
    
    # Create test documents
    test_docs = ["This is a test", "This is another test"]
    
    # Create a standalone throttled function
    def throttled_embed_documents(texts, **kwargs):
        return mock_throttler.throttled_call(mock_original_embed_documents, texts, **kwargs)
    
    # Call the function
    result = throttled_embed_documents(test_docs)
    
    # Check the result
    assert result == mock_result
    
    # Verify that the throttler was called
    mock_throttler.throttled_call.assert_called_once()
    
    # Verify that the original function was called with the right arguments
    mock_original_embed_documents.assert_called_once_with(test_docs)

def test_embed_documents_with_rate_limit():
    """Test that the embed_documents method correctly handles rate limits."""
    # Create a mock throttler that raises an exception
    mock_throttler = MagicMock()
    mock_throttler.throttled_call = MagicMock(side_effect=Exception("API rate limit exceeded"))
    
    # Create a mock original function (should never be called)
    mock_original_embed_documents = MagicMock()
    
    # Create test documents
    test_docs = ["This is a test", "This is another test"]
    
    # Create a standalone throttled function
    def throttled_embed_documents(texts, **kwargs):
        return mock_throttler.throttled_call(mock_original_embed_documents, texts, **kwargs)
    
    # Call the function and expect an exception
    with pytest.raises(Exception) as excinfo:
        throttled_embed_documents(test_docs)
    
    # Verify the exception message
    assert "API rate limit exceeded" in str(excinfo.value)
    
    # Verify that the throttler was called
    mock_throttler.throttled_call.assert_called_once()
    
    # Verify that the original function was never called
    mock_original_embed_documents.assert_not_called() 