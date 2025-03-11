"""
This module implements a Langchain chain for interacting with the NHL API.
It provides functionality to query various NHL endpoints and parse responses.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from langchain_core.runnables import RunnableConfig, RunnableSequence
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langchain.chains.base import Chain
from langchain.chains import TransformChain, SequentialChain
import requests
import json
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

QUERY_PROMPT = """You are an NHL API expert. Convert the following natural language query into an API request specification.
Available endpoints and their required parameters:

1. Current Data Endpoints (NO path parameters required):
- /player-spotlight (GET) - Get player spotlight information
- /schedule/now (GET) - Get current schedule
- /score/now (GET) - Get current scores
- /skater-stats-leaders/current (GET) - Get current skater stats leaders
  Optional Parameters:
  - categories: Stats categories to retrieve
  - limit: Number of players to return

2. Date-Specific Endpoints (require date parameter):
- /schedule/{{date}} (GET) - Get schedule for specific date
  Required path_params: {{"date": "YYYY-MM-DD"}}
- /score/{{date}} (GET) - Get scores for specific date
  Required path_params: {{"date": "YYYY-MM-DD"}}

3. Historical Data Endpoints:
- /standings-season (GET) - Get standings seasons (no parameters required)
- /skater-stats-leaders/{{season}}/{{game-type}} (GET) - Get historical skater stats leaders
  Required path_params: 
  - season: 8-digit format (e.g., "20232024")
  - game-type: integer
  Optional params:
  - categories: Stats categories to retrieve
  - limit: Number of players to return

For current data, use the /now endpoints instead of providing a date.
For example:
- "Get current scores" → use /score/now
- "Show today's schedule" → use /schedule/now
- "Get live scores" → use /score/now

Query: {query}

Respond with a JSON object containing:
- endpoint: The API endpoint to use
- params: Query parameters (if any)
- path_params: Path parameters (if any)

Example Responses:

1. Current scores:
{{
    "endpoint": "/score/now",
    "params": {{}},
    "path_params": {{}}
}}

2. Specific date schedule:
{{
    "endpoint": "/schedule/{{date}}",
    "params": {{}},
    "path_params": {{"date": "2024-03-11"}}
}}

3. Top scorers:
{{
    "endpoint": "/skater-stats-leaders/current",
    "params": {{"categories": "points", "limit": 10}},
    "path_params": {{}}
}}

Response:"""

class NHLAPIChain(Chain):
    """Chain for interacting with the NHL API."""
    
    base_url: str = "https://api-web.nhle.com/v1"
    
    @property
    def input_keys(self) -> list:
        """Input keys for the chain."""
        return ["endpoint", "params", "path_params"]
    
    @property
    def output_keys(self) -> list:
        """Output keys for the chain."""
        return ["response"]
    
    def _call(self, inputs: Dict[str, Any], run_manager: Optional[RunnableConfig] = None) -> Dict[str, Any]:
        """Execute the chain.
        
        Args:
            inputs: Dictionary with keys:
                - endpoint: The NHL API endpoint to query (e.g., "/score/now", "/player-spotlight")
                - params: Optional query parameters
                - path_params: Optional path parameters for URL construction
            run_manager: Optional configuration for the run
            
        Returns:
            Dictionary containing the API response
        """
        endpoint = inputs["endpoint"]
        params = inputs.get("params", {})
        path_params = inputs.get("path_params", {})
        
        try:
            # Format the endpoint with path parameters if any
            formatted_endpoint = endpoint.format(**path_params) if path_params else endpoint
            
            # Construct the full URL
            url = f"{self.base_url}{formatted_endpoint}"
            
            # Make the API request
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            # Parse the JSON response
            data = response.json()
            
            return {"response": data}
            
        except KeyError as e:
            # Handle missing path parameters
            missing_param = str(e).strip("'")
            return {"response": {"error": f"Missing path parameter: {missing_param}"}}
        except requests.exceptions.RequestException as e:
            return {"response": {"error": f"API request failed: {str(e)}"}}
        except Exception as e:
            return {"response": {"error": f"Unexpected error: {str(e)}"}}

    @property
    def _chain_type(self) -> str:
        return "nhl_api_chain"

class NHLResponseParser(BaseModel):
    """Parser for NHL API responses."""
    
    response: Dict[str, Any] = Field(description="Raw NHL API response")
    
    def parse_player_spotlight(self) -> Dict[str, Any]:
        """Parse player spotlight response."""
        return {
            "parsed_data": {
                "type": "player_spotlight",
                "data": self.response
            }
        }
    
    def parse_schedule(self) -> Dict[str, Any]:
        """Parse schedule response."""
        return {
            "parsed_data": {
                "type": "schedule",
                "data": self.response
            }
        }
    
    def parse_standings(self) -> Dict[str, Any]:
        """Parse standings response."""
        return {
            "parsed_data": {
                "type": "standings",
                "data": self.response
            }
        }
    
    def parse_scores(self) -> Dict[str, Any]:
        """Parse scores response."""
        return {
            "parsed_data": {
                "type": "scores",
                "data": self.response
            }
        }
    
    def parse_stats_leaders(self) -> Dict[str, Any]:
        """Parse stats leaders response."""
        return {
            "parsed_data": {
                "type": "stats_leaders",
                "data": self.response
            }
        }

def create_nhl_chain() -> Chain:
    """Create a chain for querying the NHL API and parsing responses."""
    return NHLAPIChain()

def get_formatted_date(date_str: str) -> str:
    """Convert various date strings to YYYY-MM-DD format."""
    today = datetime.now()
    
    if date_str.lower() == "today":
        return today.strftime("%Y-%m-%d")
    elif date_str.lower() == "yesterday":
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    elif date_str.lower() == "tomorrow":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # If it's already in YYYY-MM-DD format, return as is
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        # If we can't parse the date, default to today
        return today.strftime("%Y-%m-%d")

def get_current_season() -> str:
    """Get the current NHL season in the format YYYYYYYY."""
    today = datetime.now()
    if today.month < 9:  # NHL season ends in June
        return f"{today.year-1}{today.year}"
    return f"{today.year}{today.year+1}"

def extract_message_content(message: AIMessage) -> str:
    """Extract content from an AIMessage."""
    return message.content

def parse_llm_output(llm_output: str) -> Dict[str, Any]:
    """Parse LLM output into API specification."""
    try:
        return json.loads(llm_output)
    except json.JSONDecodeError:
        raise ValueError("Failed to parse LLM output as JSON")

def prepare_api_params(api_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare API parameters with proper date and season handling."""
    # Ensure params and path_params exist
    if "params" not in api_spec:
        api_spec["params"] = {}
    if "path_params" not in api_spec:
        api_spec["path_params"] = {}
        
    # Handle date parameters
    if "path_params" in api_spec and "date" in api_spec["path_params"]:
        api_spec["path_params"]["date"] = get_formatted_date(api_spec["path_params"]["date"])
    
    # Handle season parameter
    if "path_params" in api_spec and "season" in api_spec["path_params"]:
        if api_spec["path_params"]["season"] == "current":
            api_spec["path_params"]["season"] = get_current_season()
            
    return api_spec

def query_nhl(query: str, debug: bool = False) -> Dict[str, Any]:
    """Query the NHL API using natural language.
    
    Args:
        query: Natural language query about NHL data
        debug: Whether to print debug information
        
    Returns:
        Parsed response from the NHL API
    """
    try:
        # Create the query chain
        llm = ChatOpenAI(temperature=0)
        prompt = PromptTemplate(template=QUERY_PROMPT, input_variables=["query"])
        
        # Create the runnable sequence
        query_chain = (
            prompt 
            | llm 
            | extract_message_content 
            | parse_llm_output 
            | prepare_api_params
        )
        
        # Execute the chain
        api_spec = query_chain.invoke({"query": query})
        
        if debug:
            print("\nAPI Specification:")
            print(json.dumps(api_spec, indent=2))
        
        # Create and invoke the NHL API chain
        nhl_chain = create_nhl_chain()
        response = nhl_chain.invoke(api_spec)
        
        if debug:
            print("\nRaw API Response:")
            print(json.dumps(response, indent=2))
        
        # Parse the response if successful
        if "error" not in response["response"]:
            parser = NHLResponseParser(response=response["response"])
            endpoint = api_spec["endpoint"]
            
            if "player-spotlight" in endpoint:
                return parser.parse_player_spotlight()
            elif "schedule" in endpoint:
                return parser.parse_schedule()
            elif "standings" in endpoint:
                return parser.parse_standings()
            elif "score" in endpoint:
                return parser.parse_scores()
            elif "stats-leaders" in endpoint:
                return parser.parse_stats_leaders()
            else:
                return {
                    "parsed_data": {
                        "type": "raw",
                        "data": response["response"]
                    }
                }
        
        return response
        
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Error processing query: {str(e)}"}

# Example usage:
if __name__ == "__main__":
    # Test queries one at a time with debug output
    queries = [
        "What are the current NHL scores?",
        "Show me today's schedule",
        "Who are the top 5 point leaders this season?"
    ]
    
    for query in queries:
        print(f"\n{'='*50}")
        print(f"Testing query: {query}")
        print('='*50)
        
        result = query_nhl(query, debug=True)
        
        print("\nFinal Result:")
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(json.dumps(result, indent=2))
        
        input("\nPress Enter to continue to next query...") 