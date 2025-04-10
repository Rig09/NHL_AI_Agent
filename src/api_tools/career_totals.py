import requests
from utils.database_init import run_query_mysql

def get_nhl_player_career_stats(db, player_name):
    player_id = find_player_id(db, player_name)
    if not player_id:
        return {"error": "Player not found"}
    print(player_id)
    
    url = f"https://api-web.nhle.com/v1/player/{player_id}/landing"
    response = requests.get(url)
    
    if response.status_code != 200:
        return {"error": "Failed to fetch data", "status_code": response.status_code}
    
    data = response.json()
    
    # Extract career stats
    career_totals = data.get("careerTotals", {})
    regular_season_stats = career_totals.get("regularSeason", {})
    playoff_stats = career_totals.get("playoffs", {})
    
    return {
        "playerId": player_id,
        "fullName": f"{data.get('firstName', {}).get('default', '')} {data.get('lastName', {}).get('default', '')}",
        "team": data.get("fullTeamName", {}).get("default", ""),
        "regularSeason": regular_season_stats,
        "playoffs": playoff_stats,
    }


def find_player_id(db, player_name):
    query = f"""SELECT playerId FROM bio_info WHERE name LIKE '%{player_name}%'
            """
    print(query)
    result = run_query_mysql(query, db)
    
    if result and isinstance(result, list) and isinstance(result[0], dict):
        return result[0].get("playerId")
    
    return None

