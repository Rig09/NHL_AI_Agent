from app import get_secrets_or_env
from utils.database_init import init_db
from shot_maps.shot_map_plotting import extract_shot_data

def interactive_goal_map_scatter_get(db, player_name, season_lower_bound, season_upper_bound, situation, season_type):
    """
    Extracts shot data for a given player, season, situation, and shot result type
    and generates links for the game center page for each game containing a goal scored by the player
    """
    shot_data = extract_shot_data(db, player_name, season_lower_bound, season_upper_bound, situation, 'GOAL', season_type)
    
       
    # Process each goal
    for index, row in shot_data.iterrows():
        game_id = row['game_id']
        season = row['season']
        period = row['period']
        time = row['time']
        
        print(f"\nProcessing goal: Season {season}, Game {game_id}, Period {period}, Time {time}")
        
        # Format game_url using season and game_id
        # TODO: Understand boundaries on seasons where urls will have highlights
        game_url = f"https://www.nhl.com/gamecenter/{season}0{game_id}"
        
        # Add game URLs to the DataFrame
        shot_data.loc[index, 'game_url'] = game_url
    
    print("\nGoal data with game URLs:")
    print(shot_data[['game_id', 'period', 'time', 'game_url']].to_string())
    
    return shot_data

if __name__ == "__main__":
    MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, open_ai_key = get_secrets_or_env(remote=True)
    db = init_db(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE)
    interactive_goal_map_scatter_get(db, 'Zach Hyman', 2023, 2023, 'all', 'regular')