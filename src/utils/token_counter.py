import tiktoken
import numpy as np
from typing import Dict, List, Union, Any, Optional

def num_tokens_from_string(string: str, model: str = "gpt-4") -> int:
    """
    Returns the number of tokens in a text string for a specific model.
    
    Args:
        string: The string to count tokens for
        model: The name of the model to use for tokenization
        
    Returns:
        int: The number of tokens in the string
    """
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(string))

def estimate_tokens_from_messages(messages: List[Dict[str, str]], model: str = "gpt-4") -> int:
    """
    Estimates the number of tokens in a list of messages for a specific model.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        model: The name of the model to use for tokenization
        
    Returns:
        int: An estimate of the total tokens in the messages
    """
    encoding = tiktoken.encoding_for_model(model)
    
    # Per OpenAI's formula:
    # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    
    tokens_per_message = 3  # every message follows <|start|>{role/name}\n{content}<|end|>\n
    tokens_per_name = 1     # if there's a name, the role is omitted
    
    # Different models have different token counts per message
    if model.startswith("gpt-4"):
        tokens_per_message = 3
        tokens_per_name = 1
    elif model.startswith("gpt-3.5-turbo"):
        tokens_per_message = 4  # Every message follows <|im_start|>{role/name}\n{content}<|im_end|>\n
        tokens_per_name = -1  # If there's a name, the role is still included
    
    token_count = 0
    for message in messages:
        token_count += tokens_per_message
        for key, value in message.items():
            if isinstance(value, str):
                token_count += len(encoding.encode(value))
                if key == "name":
                    token_count += tokens_per_name
    
    # For the final response
    token_count += 3  # Every response is primed with <|start|>assistant
    
    return token_count

def estimate_completion_tokens(prompt_tokens: int, model: str = "gpt-4") -> int:
    """
    Provides a rough estimate of completion tokens based on prompt tokens.
    This is just a heuristic and actual values will vary.
    
    Args:
        prompt_tokens: Number of tokens in the prompt
        model: Model name
        
    Returns:
        int: Estimated completion tokens
    """
    # These are very rough estimates and should be adjusted based on observations
    if model.startswith("gpt-4"):
        # GPT-4 tends to be more verbose
        return min(int(prompt_tokens * 2.5), 4000)
    elif model.startswith("gpt-3.5"):
        # GPT-3.5 tends to be less verbose
        return min(int(prompt_tokens * 1.5), 2000)
    else:
        # Default fallback
        return min(int(prompt_tokens * 2), 3000)

def estimate_request_tokens(
    input_text: Union[str, List[Dict[str, str]]],
    model: str = "gpt-4",
    include_completion: bool = True
) -> Dict[str, int]:
    """
    Estimates tokens for an OpenAI API request, including both prompt and 
    estimated completion tokens.
    
    Args:
        input_text: Either a string or a list of message dictionaries
        model: The model being used
        include_completion: Whether to include estimated completion tokens
        
    Returns:
        Dict with prompt_tokens, completion_tokens (estimated), and total_tokens
    """
    prompt_tokens = 0
    
    # Handle different input formats
    if isinstance(input_text, str):
        prompt_tokens = num_tokens_from_string(input_text, model)
    elif isinstance(input_text, list) and all(isinstance(m, dict) for m in input_text):
        prompt_tokens = estimate_tokens_from_messages(input_text, model)
    else:
        raise ValueError("Input must be either a string or a list of message dictionaries")
    
    # Estimate completion tokens if requested
    completion_tokens = 0
    if include_completion:
        completion_tokens = estimate_completion_tokens(prompt_tokens, model)
    
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens
    } 