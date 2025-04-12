# OpenAI API Throttling

This module provides API throttling functionality for the NHL Chatbot application to avoid OpenAI API rate limits and control costs.

## Components

1. **SimpleOpenAIThrottler** (`api_throttler.py`): 
   - Core rate limiting functionality
   - Tracks requests using Streamlit session state
   - Enforces requests-per-minute limits

2. **ThrottledChatOpenAI** (`openai_chat.py`):
   - Wrapper around LangChain's ChatOpenAI
   - Applies throttling to all API calls

3. **ThrottledOpenAIEmbeddings** (`embeddings.py`):
   - Wrapper around OpenAI embeddings
   - Applies throttling to embedding generation

## Usage

### Basic Usage

```python
from utils.throttling import ThrottledChatOpenAI, ThrottledOpenAIEmbeddings

# Create a throttled OpenAI client
client = ThrottledChatOpenAI(
    api_key="your_api_key",
    model="gpt-4o",
    requests_per_minute=60  # Default is 60
)

# Use it like a normal LangChain ChatOpenAI instance
response = client.invoke({"input": "Hello, world!"})

# Create throttled embeddings
embeddings = ThrottledOpenAIEmbeddings(
    api_key="your_api_key",
    model="text-embedding-3-small"
)

# Use it like a normal OpenAI embeddings instance
vector = embeddings.embed_query("Hello, world!")
```

### In the Streamlit App

The throttling is already integrated into the app. When rate limits are exceeded, users will see a friendly error message telling them to try again in a few seconds.

## Rate Limiting Behavior

- Requests are tracked using timestamps stored in Streamlit's session state
- When a rate limit is exceeded, an exception is raised with a message explaining how long to wait
- Old request timestamps (older than 1 minute) are automatically cleaned up

## Testing

We use pytest for testing the throttling functionality. Tests are located in the `tests/utils/throttling/` directory.

Run tests:

```bash
# Run all tests
./run_tests.sh

# Run specific test files
python -m pytest tests/utils/throttling/test_api_throttling.py

# Run with coverage report
python -m pytest --cov=src.utils.throttling --cov-report=term-missing
```

## Customization

You can adjust the rate limits by modifying the `requests_per_minute` parameter when creating the throttled clients.

For advanced configurations, you could modify the `SimpleOpenAIThrottler` class to add:
- Token-based limits
- Persistent storage for tracking between sessions
- User-based rate limits
- Waiting instead of raising exceptions 