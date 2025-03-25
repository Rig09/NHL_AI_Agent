"""
This module implements a Langchain chain for interacting with the NHL API.
It provides functionality to query various NHL endpoints and parse responses.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from langchain_core.runnables import RunnableConfig, RunnableSequence, RunnablePassthrough
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
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

def extract_relevant_data(endpoint: str, response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract only the relevant parts of the API response based on the endpoint."""
    try:
        if "player-spotlight" in endpoint:
            return {"player_spotlight": response_data.get("players", [])}
        elif "schedule" in endpoint:
            return {"games": response_data.get("dates", [])}
        elif "standings" in endpoint:
            return {"standings": response_data.get("records", [])}
        elif "score" in endpoint:
            return {"scores": response_data.get("games", [])}
        elif "stats-leaders" in endpoint:
            return {"leaders": response_data.get("playerStats", [])}
        else:
            # Fallback: Return the entire response if not recognized
            return {"data": response_data}
    except Exception as e:
        return {"error": str(e)}


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

Return only JSON and no additional text.
- Ensure proper JSON format with key-value pairs.
- Provide clear and concise information without extra commentary.

DO NOT INCLUDE ``` or a heading of json or JSON in your response. This will be passed directly, ONLY PROVIDE THE JSON output. Do not add any formating or tittle. DO NOT INCLUDE ```.

Provide the JSON output:"""

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

def create_nhl_api_chain() -> Chain:
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
        raise ValueError(f"Failed to parse LLM output as JSON Output was: {llm_output}")

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

def processJSON_chain(llm, original_query, json_output) -> str :
    """Take in the JSON from the query and return a natural language response."""
    template = """
    You are a helpful assistant that takes in information in the form of a JSON response and returns a clear, concise natural language answer to a user query.
    
    The users original question was: {original_query}
    The API call returned the following data: {json_output}
    
    Please respond in a conversational tone with an appropriate level of detail.
    If the API data is empty or incomplete, respond with a helpful explanation.
    """
    prompt = ChatPromptTemplate.from_template(template)

    processing_chain = (
         prompt
        | llm
        | StrOutputParser()
    )
    return processing_chain.invoke({'original_query': original_query, 'json_output': json_output})


import json

def query_nhl(llm, query: str, debug: bool = False) -> Dict[str, Any]:
    """Query the NHL API using natural language.
    
    Args:
        llm: The language model to use for the query
        query: Natural language query about NHL data
        debug: Whether to print debug information
        
    Returns:
        Parsed response from the NHL API
    """
    try:
        # Create the query chain
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
        nhl_chain = create_nhl_api_chain()
        response = nhl_chain.invoke(api_spec)
        
        if debug:
            print("\nRaw API Response:")
            print(json.dumps(response, indent=2))
        
        # Handle API errors
        if not response or "error" in response.get("response", {}):
            return {"error": response.get("response", {}).get("error", "Unknown API error")}

        # Parse the response if successful
        parser = NHLResponseParser(response=response["response"])
        endpoint = api_spec["endpoint"]
        
        if "player-spotlight" in endpoint:
            result = parser.parse_player_spotlight()
        elif "schedule" in endpoint:
            result = parser.parse_schedule()
        elif "standings" in endpoint:
            result = parser.parse_standings()
        elif "score" in endpoint:
            result = parser.parse_scores()
        elif "stats-leaders" in endpoint:
            result = parser.parse_stats_leaders()
        else:
            result = {
                "parsed_data": {
                    "type": "raw",
                    "data": response["response"]
                }
            }

        #relevant_data = extract_relevant_data(endpoint, response["response"])    

        # Convert API output to natural language using processJSON_chain
        final_result = processJSON_chain(llm, query, response["response"])
        
        if debug:
            print("\nFinal Natural Language Response:")
            print(final_result)
        
        return final_result
        
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
        llm = ChatOpenAI(temperature=0)
        
        print(f"\n{'='*50}")
        print(f"Testing query: {query}")
        print('='*50)
        
        result = query_nhl(llm, query, debug=False)
        
        print("\nFinal Result:")
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(json.dumps(result, indent=2))
        
        input("\nPress Enter to continue to next query...") 