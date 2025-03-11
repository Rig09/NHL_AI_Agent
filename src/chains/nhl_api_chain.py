"""
This module implements a Langchain chain for interacting with the NHL API.
It provides functionality to query various NHL endpoints and parse responses.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field
from langchain.chains.base import Chain
from langchain.chains import TransformChain, SequentialChain
import requests
import json

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
        
        # Format the endpoint with path parameters if any
        formatted_endpoint = endpoint.format(**path_params) if path_params else endpoint
        
        # Construct the full URL
        url = f"{self.base_url}{formatted_endpoint}"
        
        try:
            # Make the API request
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            # Parse the JSON response
            data = response.json()
            
            return {"response": data}
            
        except requests.exceptions.RequestException as e:
            return {"response": {"error": str(e)}}

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
    """Create a chain for querying the NHL API and parsing responses.
    
    Returns:
        A sequential chain that handles API requests and response parsing
    """
    # Create the API chain
    api_chain = NHLAPIChain()
    
    # Create a transform chain for parsing responses
    def transform_func(inputs: dict) -> dict:
        parser = NHLResponseParser(response=inputs["response"])
        
        # Determine which parser to use based on the endpoint
        endpoint = inputs["endpoint"]
        
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
        
        # Default to returning raw response if no specific parser
        return {
            "parsed_data": {
                "type": "raw",
                "data": inputs["response"]
            }
        }
    
    parser_chain = TransformChain(
        input_variables=["response", "endpoint"],
        output_variables=["parsed_data"],
        transform=transform_func
    )
    
    # Combine the chains
    return SequentialChain(
        chains=[api_chain, parser_chain],
        input_variables=["endpoint", "params", "path_params"],
        output_variables=["parsed_data"]
    )

# Example usage:
if __name__ == "__main__":
    chain = create_nhl_chain()
    
    # Example 1: Get current scores
    scores_result = chain.invoke({
        "endpoint": "/score/now",
        "params": {},
        "path_params": {}
    })
    
    # Example 2: Get schedule for a specific date
    schedule_result = chain.invoke({
        "endpoint": "/schedule/{date}",
        "params": {},
        "path_params": {"date": datetime.now().strftime("%Y-%m-%d")}
    })
    
    # Example 3: Get skater stats leaders
    leaders_result = chain.invoke({
        "endpoint": "/skater-stats-leaders/current",
        "params": {
            "categories": "points",
            "limit": 10
        },
        "path_params": {}
    })
    
    # Print results
    print("\nCurrent Scores:")
    print(json.dumps(scores_result, indent=2))
    
    print("\nToday's Schedule:")
    print(json.dumps(schedule_result, indent=2))
    
    print("\nStats Leaders:")
    print(json.dumps(leaders_result, indent=2)) 