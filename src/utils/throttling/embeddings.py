from langchain_openai import OpenAIEmbeddings
from .api_throttler import SimpleOpenAIThrottler
from typing import List, Optional, Any
import functools
from pydantic import model_validator, ConfigDict
import os

class ThrottledOpenAIEmbeddings(OpenAIEmbeddings):
    """
    A wrapper around the LangChain OpenAIEmbeddings class that applies basic throttling
    to avoid rate limits.
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, api_key=None, model="text-embedding-3-small", **kwargs):
        """
        Initialize the throttled OpenAI embeddings client.
        
        Args:
            api_key: The OpenAI API key
            model: The embedding model name to use
            **kwargs: Additional kwargs to pass to the OpenAIEmbeddings constructor
        """
        # Initialize the OpenAI embeddings
        super().__init__(
            api_key=api_key,
            model=model,
            **kwargs
        )
        
        # Create the throttler
        self._throttler = SimpleOpenAIThrottler(requests_per_minute=60)
        
        # Store original methods
        self._original_embed_documents = super().embed_documents
        self._original_embed_query = super().embed_query
        
        # Create throttled versions of the methods
        self._throttled_embed_documents = self._create_throttled_embed_documents()
        self._throttled_embed_query = self._create_throttled_embed_query()
    
    def _create_throttled_embed_documents(self):
        """Create a throttled version of the embed_documents method"""
        @functools.wraps(self._original_embed_documents)
        def throttled_embed_documents(texts: List[str], **kwargs) -> List[List[float]]:
            return self._throttler.throttled_call(self._original_embed_documents, texts, **kwargs)
        return throttled_embed_documents
    
    def _create_throttled_embed_query(self):
        """Create a throttled version of the embed_query method"""
        @functools.wraps(self._original_embed_query)
        def throttled_embed_query(text: str, **kwargs) -> List[float]:
            return self._throttler.throttled_call(self._original_embed_query, text, **kwargs)
        return throttled_embed_query
    
    def embed_documents(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Override the embed_documents method with the throttled version"""
        return self._throttled_embed_documents(texts, **kwargs)
    
    def embed_query(self, text: str, **kwargs) -> List[float]:
        """Override the embed_query method with the throttled version"""
        return self._throttled_embed_query(text, **kwargs) 