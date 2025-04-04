import pandas as pd
import numpy as np
from datetime import date
from utils.database_init import run_query_mysql


def game_information(db, situation: str, game_ids: list[int]):
    game_ids_str = ', '.join(map(str, game_ids))  # Convert list to a comma-separated string
    query = f"""
                SELECT * FROM game_logs WHERE gameid in ({game_ids_str}) AND situation = '{situation}'
            """
    result = run_query_mysql(query, db)
    if not result:  # Handle empty or None results
        return "No game data found for the given situation and game IDs."

    # Convert to DataFrame
    games_df = pd.DataFrame(result)

    # Return as a nicely formatted string
    return games_df.to_string(index=False)  # Formats it in a readable table

    