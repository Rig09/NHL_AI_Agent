import time
from datetime import datetime, timedelta
import streamlit as st

class SimpleOpenAIThrottler:
    """
    A minimal implementation of API throttling for OpenAI API calls.
    Tracks request count and implements basic rate limiting.
    """
    
    def __init__(self, requests_per_minute=60):
        """
        Initialize the throttler with rate limits.
        
        Args:
            requests_per_minute: Maximum number of requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self._initialize_tracking()
    
    def _initialize_tracking(self):
        """Initialize the request tracking in session state"""
        if "openai_throttle" not in st.session_state:
            st.session_state.openai_throttle = {
                "timestamps": []
            }
    
    def check_rate_limit(self):
        """
        Check if the current request is within rate limits.
        
        Returns:
            bool: True if the request can proceed, False otherwise
        """
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean up old timestamps
        st.session_state.openai_throttle["timestamps"] = [
            ts for ts in st.session_state.openai_throttle["timestamps"]
            if ts > minute_ago
        ]
        
        # Check if we're under the limit
        return len(st.session_state.openai_throttle["timestamps"]) < self.requests_per_minute
    
    def record_request(self):
        """Record that a request has been made"""
        st.session_state.openai_throttle["timestamps"].append(datetime.now())
    
    def throttled_call(self, func, *args, **kwargs):
        """
        Execute a function with throttling.
        
        Args:
            func: The function to call
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of calling func(*args, **kwargs)
            
        Raises:
            Exception: If the rate limit is exceeded
        """
        if not self.check_rate_limit():
            # If we can't proceed, raise an exception
            # This could be modified to wait instead
            time_to_wait = 60 - (datetime.now() - min(st.session_state.openai_throttle["timestamps"])).total_seconds()
            raise Exception(f"API rate limit exceeded. Please try again in {int(time_to_wait)} seconds.")
        
        # Execute the function
        result = func(*args, **kwargs)
        
        # Record the request
        self.record_request()
        
        return result 