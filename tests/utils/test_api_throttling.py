import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import streamlit as st
from src.utils.throttling import SimpleOpenAIThrottler

@pytest.fixture(autouse=True)
def setup_mock_session_state():
    """Set up the streamlit session state for testing."""
    if not hasattr(st.session_state, 'openai_throttle'):
        st.session_state.openai_throttle = {"timestamps": []}

def test_initialize_tracking(setup_mock_session_state):
    """Test that tracking is initialized properly."""
    # Delete the key if it exists
    if hasattr(st.session_state, 'openai_throttle'):
        delattr(st.session_state, 'openai_throttle')
    
    # Initialize the throttler which should create the session state
    throttler = SimpleOpenAIThrottler(requests_per_minute=60)
    
    # Check if openai_throttle is in session_state
    assert hasattr(st.session_state, 'openai_throttle')
    
    # Check if the timestamps list is initialized
    assert "timestamps" in st.session_state.openai_throttle
    assert isinstance(st.session_state.openai_throttle["timestamps"], list)
    assert len(st.session_state.openai_throttle["timestamps"]) == 0

def test_check_rate_limit_under_limit(setup_mock_session_state):
    """Test that rate limiting allows requests when under the limit."""
    throttler = SimpleOpenAIThrottler(requests_per_minute=60)
    
    # Mock 5 timestamps (under the limit)
    st.session_state.openai_throttle["timestamps"] = [
        datetime.now() - timedelta(seconds=10*i) for i in range(5)
    ]
    
    # Should be allowed to proceed
    assert throttler.check_rate_limit() == True

def test_check_rate_limit_at_limit(setup_mock_session_state):
    """Test that rate limiting blocks requests when at the limit."""
    throttler = SimpleOpenAIThrottler(requests_per_minute=5)
    
    # Mock 5 timestamps (at the limit)
    st.session_state.openai_throttle["timestamps"] = [
        datetime.now() - timedelta(seconds=10*i) for i in range(5)
    ]
    
    # Should not be allowed to proceed
    assert throttler.check_rate_limit() == False

def test_check_rate_limit_old_timestamps_removed(setup_mock_session_state):
    """Test that old timestamps are cleaned up."""
    throttler = SimpleOpenAIThrottler(requests_per_minute=60)
    
    now = datetime.now()
    
    # Add 5 recent timestamps and 5 old timestamps
    recent_timestamps = [now - timedelta(seconds=i*10) for i in range(5)]
    old_timestamps = [now - timedelta(seconds=i*10 + 70) for i in range(5)]  # Older than 1 minute
    
    st.session_state.openai_throttle["timestamps"] = recent_timestamps + old_timestamps
    
    # Check rate limit, which should clean up old timestamps
    throttler.check_rate_limit()
    
    # Only recent timestamps should remain
    assert len(st.session_state.openai_throttle["timestamps"]) == 5
    for ts in st.session_state.openai_throttle["timestamps"]:
        assert (now - ts).total_seconds() < 60

def test_record_request(setup_mock_session_state):
    """Test that requests are recorded correctly."""
    throttler = SimpleOpenAIThrottler(requests_per_minute=60)
    
    # Clear any existing timestamps
    st.session_state.openai_throttle["timestamps"] = []
    
    # Record a request
    throttler.record_request()
    
    # Check that a timestamp was added
    assert len(st.session_state.openai_throttle["timestamps"]) == 1
    
    # Record another request
    throttler.record_request()
    
    # Check that another timestamp was added
    assert len(st.session_state.openai_throttle["timestamps"]) == 2

def test_throttled_call_success(setup_mock_session_state):
    """Test that throttled_call executes the function when under the limit."""
    throttler = SimpleOpenAIThrottler(requests_per_minute=60)
    
    # Clear any existing timestamps
    st.session_state.openai_throttle["timestamps"] = []
    
    # Mock function
    mock_func = MagicMock(return_value="Success")
    
    # Call the function through throttled_call
    result = throttler.throttled_call(mock_func, "arg1", key="value")
    
    # Check that the function was called with the right arguments
    mock_func.assert_called_once_with("arg1", key="value")
    
    # Check that the result was returned
    assert result == "Success"
    
    # Check that the request was recorded
    assert len(st.session_state.openai_throttle["timestamps"]) == 1

def test_throttled_call_rate_limited(setup_mock_session_state):
    """Test that throttled_call raises an exception when rate limited."""
    throttler = SimpleOpenAIThrottler(requests_per_minute=5)
    
    # Set up timestamps at the limit
    now = datetime.now()
    st.session_state.openai_throttle["timestamps"] = [
        now - timedelta(seconds=i*10) for i in range(5)
    ]
    
    # Mock function
    mock_func = MagicMock(return_value="Success")
    
    # Call should raise an exception
    with pytest.raises(Exception) as excinfo:
        throttler.throttled_call(mock_func, "arg1", key="value")
    
    # Check that the exception message contains expected text
    assert "API rate limit exceeded" in str(excinfo.value)
    
    # The function should not have been called
    mock_func.assert_not_called()
    
    # No new timestamp should have been added
    assert len(st.session_state.openai_throttle["timestamps"]) == 5 