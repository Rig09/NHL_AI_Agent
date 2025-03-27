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
  - game-type: integer (1=regular season, 2=playoffs, 3=pre-season)
  Optional params:
  - categories: Stats categories to retrieve
  - limit: Number of players to return

4. Player Information Endpoints:
- /player/{{playerId}} (GET) - Get detailed player information
  Required path_params: {{"playerId": "player_id"}}
- /player/{{playerId}}/landing (GET) - Get player landing page data
  Required path_params: {{"playerId": "player_id"}}
- /player/{{playerId}}/stats (GET) - Get player statistics
  Required path_params: {{"playerId": "player_id"}}
  Optional params:
  - stats: Stats categories to retrieve
  - season: Season to get stats for (format: YYYY-YYYY)

5. Team Information Endpoints:
- /team/{{teamId}} (GET) - Get team information
  Required path_params: {{"teamId": "team_id"}}
- /team/{{teamId}}/roster (GET) - Get team roster
  Required path_params: {{"teamId": "team_id"}}
- /team/{{teamId}}/schedule (GET) - Get team schedule
  Required path_params: {{"teamId": "team_id"}}
  Optional params:
  - startDate: Start date (YYYY-MM-DD)
  - endDate: End date (YYYY-MM-DD)

6. Game Information Endpoints:
- /game/{{gameId}} (GET) - Get game information
  Required path_params: {{"gameId": "game_id"}}
- /game/{{gameId}}/feed/live (GET) - Get live game feed
  Required path_params: {{"gameId": "game_id"}}
- /game/{{gameId}}/feed/live/diffPatch (GET) - Get live game feed updates
  Required path_params: {{"gameId": "game_id"}}

7. League Information Endpoints:
- /divisions (GET) - Get all divisions
- /conferences (GET) - Get all conferences
- /teams (GET) - Get all teams
- /standings (GET) - Get current standings
  Optional params:
  - expand: team.schedule
  - season: Season to get standings for (format: YYYY-YYYY)

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
    
    def parse_player_info(self) -> Dict[str, Any]:
        """Parse player information response."""
        return {
            "parsed_data": {
                "type": "player_info",
                "data": self.response
            }
        }
    
    def parse_player_landing(self) -> Dict[str, Any]:
        """Parse player landing page response."""
        return {
            "parsed_data": {
                "type": "player_landing",
                "data": self.response
            }
        }
    
    def parse_player_stats(self) -> Dict[str, Any]:
        """Parse player statistics response."""
        return {
            "parsed_data": {
                "type": "player_stats",
                "data": self.response
            }
        }
    
    def parse_team_info(self) -> Dict[str, Any]:
        """Parse team information response."""
        return {
            "parsed_data": {
                "type": "team_info",
                "data": self.response
            }
        }
    
    def parse_team_roster(self) -> Dict[str, Any]:
        """Parse team roster response."""
        return {
            "parsed_data": {
                "type": "team_roster",
                "data": self.response
            }
        }
    
    def parse_team_schedule(self) -> Dict[str, Any]:
        """Parse team schedule response."""
        return {
            "parsed_data": {
                "type": "team_schedule",
                "data": self.response
            }
        }
    
    def parse_game_info(self) -> Dict[str, Any]:
        """Parse game information response."""
        return {
            "parsed_data": {
                "type": "game_info",
                "data": self.response
            }
        }
    
    def parse_game_feed(self) -> Dict[str, Any]:
        """Parse game feed response."""
        return {
            "parsed_data": {
                "type": "game_feed",
                "data": self.response
            }
        }
    
    def parse_divisions(self) -> Dict[str, Any]:
        """Parse divisions response."""
        return {
            "parsed_data": {
                "type": "divisions",
                "data": self.response
            }
        }
    
    def parse_conferences(self) -> Dict[str, Any]:
        """Parse conferences response."""
        return {
            "parsed_data": {
                "type": "conferences",
                "data": self.response
            }
        }
    
    def parse_teams(self) -> Dict[str, Any]:
        """Parse teams response."""
        return {
            "parsed_data": {
                "type": "teams",
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

def trim_json_data(json_data: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
    """Trim JSON data to only include relevant fields based on the endpoint."""
    if not isinstance(json_data, dict):
        return json_data
        
    if "player-spotlight" in endpoint:
        # For player spotlight, only keep essential player info
        players = json_data.get("players", [])
        trimmed_players = []
        for player in players:
            trimmed_players.append({
                "name": player.get("name"),
                "position": player.get("position"),
                "team": player.get("team"),
                "stats": {
                    "goals": player.get("stats", {}).get("goals"),
                    "assists": player.get("stats", {}).get("assists"),
                    "points": player.get("stats", {}).get("points")
                }
            })
        return {"players": trimmed_players}
    
    elif "schedule" in endpoint:
        # For schedule, only keep game times and teams
        dates = json_data.get("dates", [])
        trimmed_dates = []
        for date in dates:
            trimmed_games = []
            for game in date.get("games", []):
                trimmed_games.append({
                    "gameDate": game.get("gameDate"),
                    "homeTeam": game.get("homeTeam", {}).get("name"),
                    "awayTeam": game.get("awayTeam", {}).get("name"),
                    "status": game.get("status", {}).get("state")
                })
            trimmed_dates.append({"date": date.get("date"), "games": trimmed_games})
        return {"dates": trimmed_dates}
    
    elif "standings" in endpoint:
        # For standings, only keep team records
        records = json_data.get("records", [])
        trimmed_records = []
        for record in records:
            trimmed_records.append({
                "team": record.get("team", {}).get("name"),
                "points": record.get("points"),
                "gamesPlayed": record.get("gamesPlayed"),
                "wins": record.get("wins"),
                "losses": record.get("losses")
            })
        return {"records": trimmed_records}
    
    elif "score" in endpoint:
        # For scores, only keep game results
        games = json_data.get("games", [])
        trimmed_games = []
        for game in games:
            trimmed_games.append({
                "gameDate": game.get("gameDate"),
                "homeTeam": {
                    "name": game.get("homeTeam", {}).get("name"),
                    "score": game.get("homeTeam", {}).get("score")
                },
                "awayTeam": {
                    "name": game.get("awayTeam", {}).get("name"),
                    "score": game.get("awayTeam", {}).get("score")
                },
                "status": game.get("status", {}).get("state")
            })
        return {"games": trimmed_games}
    
    elif "stats-leaders" in endpoint:
        # For stats leaders, only keep player names and relevant stats
        stats = json_data.get("playerStats", [])
        trimmed_stats = []
        for stat in stats:
            trimmed_stats.append({
                "name": stat.get("name"),
                "team": stat.get("team"),
                "stats": {
                    k: v for k, v in stat.get("stats", {}).items() 
                    if k in ["goals", "assists", "points", "gamesPlayed"]
                }
            })
        return {"playerStats": trimmed_stats}
    
    elif "player/" in endpoint:
        # For player endpoints, keep essential player information
        if "/landing" in endpoint:
            return {
                "player": {
                    "name": json_data.get("player", {}).get("name"),
                    "position": json_data.get("player", {}).get("position"),
                    "team": json_data.get("player", {}).get("team"),
                    "stats": json_data.get("player", {}).get("stats", {})
                }
            }
        elif "/stats" in endpoint:
            return {
                "player": {
                    "name": json_data.get("player", {}).get("name"),
                    "stats": json_data.get("stats", [])
                }
            }
        else:
            return {
                "player": {
                    "name": json_data.get("name"),
                    "position": json_data.get("position"),
                    "team": json_data.get("team"),
                    "height": json_data.get("height"),
                    "weight": json_data.get("weight"),
                    "birthDate": json_data.get("birthDate"),
                    "nationality": json_data.get("nationality")
                }
            }
    
    elif "team/" in endpoint:
        # For team endpoints, keep essential team information
        if "/roster" in endpoint:
            roster = json_data.get("roster", [])
            trimmed_roster = []
            for player in roster:
                trimmed_roster.append({
                    "name": player.get("name"),
                    "position": player.get("position"),
                    "number": player.get("number")
                })
            return {"roster": trimmed_roster}
        elif "/schedule" in endpoint:
            dates = json_data.get("dates", [])
            trimmed_dates = []
            for date in dates:
                trimmed_games = []
                for game in date.get("games", []):
                    trimmed_games.append({
                        "gameDate": game.get("gameDate"),
                        "opponent": game.get("homeTeam", {}).get("name") if game.get("homeTeam", {}).get("id") == json_data.get("team", {}).get("id") else game.get("awayTeam", {}).get("name"),
                        "score": f"{game.get('homeTeam', {}).get('score')}-{game.get('awayTeam', {}).get('score')}"
                    })
                trimmed_dates.append({"date": date.get("date"), "games": trimmed_games})
            return {"schedule": trimmed_dates}
        else:
            return {
                "team": {
                    "name": json_data.get("name"),
                    "abbreviation": json_data.get("abbreviation"),
                    "division": json_data.get("division", {}).get("name"),
                    "conference": json_data.get("conference", {}).get("name")
                }
            }
    
    elif "game/" in endpoint:
        # For game endpoints, keep essential game information
        if "/feed/live" in endpoint:
            return {
                "gameData": {
                    "status": json_data.get("gameData", {}).get("status", {}).get("state"),
                    "homeTeam": json_data.get("gameData", {}).get("teams", {}).get("home", {}).get("name"),
                    "awayTeam": json_data.get("gameData", {}).get("teams", {}).get("away", {}).get("name"),
                    "score": json_data.get("liveData", {}).get("linescore", {}).get("currentPeriodOrdinal")
                },
                "liveData": {
                    "plays": json_data.get("liveData", {}).get("plays", {}).get("allPlays", [])[-5:]  # Last 5 plays
                }
            }
        else:
            return {
                "gameData": {
                    "status": json_data.get("gameData", {}).get("status", {}).get("state"),
                    "homeTeam": json_data.get("gameData", {}).get("teams", {}).get("home", {}).get("name"),
                    "awayTeam": json_data.get("gameData", {}).get("teams", {}).get("away", {}).get("name"),
                    "score": json_data.get("liveData", {}).get("linescore", {}).get("currentPeriodOrdinal")
                }
            }
    
    elif endpoint in ["/divisions", "/conferences", "/teams"]:
        # For league information endpoints, keep essential organizational data
        if endpoint == "/divisions":
            return {
                "divisions": [
                    {
                        "name": div.get("name"),
                        "conference": div.get("conference", {}).get("name")
                    } for div in json_data.get("divisions", [])
                ]
            }
        elif endpoint == "/conferences":
            return {
                "conferences": [
                    {
                        "name": conf.get("name"),
                        "divisions": [div.get("name") for div in conf.get("divisions", [])]
                    } for conf in json_data.get("conferences", [])
                ]
            }
        else:  # /teams
            return {
                "teams": [
                    {
                        "name": team.get("name"),
                        "abbreviation": team.get("abbreviation"),
                        "division": team.get("division", {}).get("name"),
                        "conference": team.get("conference", {}).get("name")
                    } for team in json_data.get("teams", [])
                ]
            }
    
    return json_data

def processJSON_chain(llm, original_query, json_output, endpoint: str) -> str:
    """Take in the JSON from the query and return a natural language response."""
    # Trim the JSON data before processing
    trimmed_data = trim_json_data(json_output, endpoint)
    
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
    return processing_chain.invoke({'original_query': original_query, 'json_output': trimmed_data})

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
        
        # Map endpoints to parser methods
        endpoint_parsers = {
            "player-spotlight": parser.parse_player_spotlight,
            "schedule": parser.parse_schedule,
            "standings": parser.parse_standings,
            "score": parser.parse_scores,
            "stats-leaders": parser.parse_stats_leaders,
            "/player/": parser.parse_player_info,
            "/player/landing": parser.parse_player_landing,
            "/player/stats": parser.parse_player_stats,
            "/team/": parser.parse_team_info,
            "/team/roster": parser.parse_team_roster,
            "/team/schedule": parser.parse_team_schedule,
            "/game/": parser.parse_game_info,
            "/game/feed/live": parser.parse_game_feed,
            "/divisions": parser.parse_divisions,
            "/conferences": parser.parse_conferences,
            "/teams": parser.parse_teams
        }
        
        # Find the appropriate parser method
        parser_method = None
        for key, method in endpoint_parsers.items():
            if key in endpoint:
                parser_method = method
                break
        
        if parser_method:
            result = parser_method()
        else:
            result = {
                "parsed_data": {
                    "type": "raw",
                    "data": response["response"]
                }
            }

        # Convert API output to natural language using processJSON_chain
        final_result = processJSON_chain(llm, query, response["response"], endpoint)
        
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