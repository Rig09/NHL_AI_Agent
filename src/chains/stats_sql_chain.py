from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.globals import set_verbose
from utils.database_init import get_table_info, run_query_mysql


set_verbose(True)

# SQLite Database URI
#db_uri = "sqlite:///SkatersStats.db"

#db = SQLDatabase.from_uri(db_uri)

#mySQL implementation
#db = init_db()

#print(db.run("SELECT * FROM RegularSeason2023 LIMIT 1")) # Test the database connection

def get_sql_chain(db, llm):

    #database functions. Get information from the databases to be used in the chain
    def get_table_schema(db):
        relevent_tables = ['SkaterStats_regular_2024', 'GoalieStats_regular_2024', 'LineStats_playoffs_2024', 'PairStats_regular_2024', 'teamstats_regular_2024']
        return get_table_info(db, relevent_tables) #return the schema of the first table in the list

    #print(run_query("SELECT * FROM RegularSeason2023 LIMIT 1")) # Test the database connection

    template = """
    Based on the table schema below, generate a valid SQL query that answers the user's question. There are four different types of tables.
    Tables for skaters, goalies, pairings, teams, and lines. Based on the statistical question it can be deduced which one is being asked about. There tables have different queries. These can be found below.
    DO NOT include explanations, comments, code blocks, or duplicate queries. Return only a single SQL query. DO NOT include ```sql or ``` in the response.
    {schema}
   
    For skaters, lines, pairs, teams, and goalies there is a table for regular season and playoffs in each year. Table names are using the following format:
    - Regular season → <playerType>Stats_regular_<year> 
    - Playoffs → <PlayerType>Stats_playoffs_<year>
    where player type refers to whether the player is a skater, goalie, pairing, line, or team. 

    Shots_data contains information on every shot taken in the NHL since 2015. More detail about how to query this table is provided below.

    Game_logs contains information about every game since the 2008 season. Each game will be listed twice, since it is listed for each team. If someone asks about a specific game or games, query this table to find information about the game.
    Game_logs only contains information about TEAM level stats. Do not use this table for any skater, goalie, or individual. An example of when to use this would be, 'What is the leafs record against the boston bruins in the last 5 years.'


    For the year. A user may say 2023-24 or 2023-2024. In this case the season is stored as the first year. So 2023-24 would be 2023.

    If a question is given in present tense, assume the user is asking about 2024-25. If no season is given, assume the user is asking about the 2024-25 season.
    For example if someone asks "Who leads the NHL in Goals" this would be the same as "who lead the NHL in goals in the 2024-25 season"
    If someone does not specify the season type assume the season is regular.

    If someone asks what 'pair', 'defensive pairing', 'd pair', or 'pairing' they mean defensive pairing from the PairStats_regular_<year> or PairStats_playoffs_<year> tables.
    If someone asks what 'line' or 'forward line'  they mean forward line from the lineStats_regular_<year> or lineStats_playoffs_<year> tables.
    pairs and lines contain multiple names that are stored in a hyphonated way like, name1-name2-name3 or just name1-name2. To account for different orders being inputed, use: 
    WHERE name LIKE '%name1%' AND name LIKE '%name2%' AND name LIKE '%name3%'; This is the way to find the line since the names may be in different orders.

    The current season is the 2024-25 season. Use this season for current stats. When no season is provided or it is unclear what season is being refered to, Use 2024. 
    If someone asks, 'what pair leads the NHL in expected goals percentage with at least 50 minutes played" Then this means to query the PairStats_regular_2024 and find the highest expected goals percentage with at least 50 minutes played.
    
    Use correct stat terms:
    - "Even strength" → "5on5", "Power play" → "5on4", "Shorthanded" → "4on5", "All situations" → "All". If strength is not defined use 'all' Do not add the total of multiple strengths together.
    If no strength is defined search in 'all' not all strengths combined. So if someone asks how many goals did a player score. The query should include where situation = 'all'  
    - "Minutes" means "icetime" (store in seconds but return in minutes & seconds). Unless specified otherwise, this means the 'icetime' for the player in situation: 'all'.  
    - "Points" = Goals + Assists.

    Expected goals percentage is a positive statistic. highest/best means the highest percentage.

    Player positions: C = Center, L = Left Wing, R = Right Wing, D = Defenseman.  
    Grouping: Forwards = (C, L, R), Skaters = (C, L, R, D).  

    Someone May request stats from a range of seasons like 'How many goals did Connor Mcdavid score from the 2018-19 season to the 2022-23 season' This means query the db and find the total for Every season in between those two inclusive. 
    In that example then, you would query for the total goals in the 2018, 2019, 2020, 2021, and 2022 seasons.

    When the user requests a total allways use the 'all' situation for the player do not add these up.
    For example, if someone were to ask how many games played a player had in a season, use only the result in 'all' DO NOT ADD THEM with others.

    If a user requests a stat per game, devide the stat by the number of games played in that same time period

    If somone asks for a stat per 60 then find the number of that stat per 60 minutes of icetime. Reminder that icetime is stored in seconds.

    Teams are stored as abbreviations (e.g., "Toronto Maple Leafs" → "TOR"). Infer references like "Leafs" → "TOR".

    When using the shots_data table, the 'isHomeTeam' attribute can be used to determine the team, the shot is either taken by the home team or not. 
    
    Then use the 'homeTeamCode' and 'awayTeamCode' attributes to determine the team. If the home team took the shot, the shot is from the homeTeamCode.

    When querying the shots_data table, the 'isPlayoffGame' attribute can be used to determine if the game is a playoff game or not. This takes the value 1 if it is a playoff game and 0 if it is a regular season game. 
    To determine the strength when querying the shots_data table, use the 'awaySkatersOnIce', 'homeSkatersOnIce' attributes. Use the is_home_team to determine whether the shots are taken by the home or away team. 
    If it is taken by the home team than the homeSkatersOnIce attribute comes first in the strenth. For example, if the shot is taken and isHomeTeam = 1, and awaySkatersOnIce = 4 and homeSkatersOnIce = 5, then the strength is 5on4. The first number corrisponds to the number of players on the ice that took the shot. 
    Use that logic, to change queries to fit with the strength if it is passed asking for a query on the shots_data table.
    
    Also note that you can tell what team took a shot by the team code attribute in shots_data.

    ALL GOALIE STATS SHOULD ONLY USE ROWS that have the situation 'all' unless otherwise specified. If someone asks what was <goalie name>'s save percentage, use the situation 'all' to find the save percentage. 
    If someone asks for a leader in a statistic for goalies without specifying the situation, this is the leader in rows with the situation 'all'.

    More information on goalies: If a user asks for goals saved above expected, this is the difference between the expected goals against and the actual goals against. or the Xgoals and goals columns. 
    If someone asks for goals saved above expected per 60 minutes, divide the goals saved above expected by the icetime in minutes and multiply by 60.
    if someone asks for goals saved above expected per expected goal faced, devide by the number of expected goals faced.
    If someone asks for save percentage, this is the number of saves divided by the number of shots faced. The number of shots faced is the coloumn 'ongoal' in the goalies tables. The saves is this number minues the goals column. 
    DO NOT USE the danger level columns to make save percentage unless specifically asked for. The abseloute total of shots faced comes from 'ongoal'. To find save percentage, divide this number minus the goals column by itself.
    For example: (ongoal - goals) / ongoal

    DO NOT USE the danger level columns to make save percentage unless specifically asked for. The abseloute total of shots faced comes from 'ongoal'. To find save percentage, divide this number minus the goals column by itself.

    Goals against average, is the goals against divided by the icetime in minutes and multiplied by 60.
    If not specified assume the save percentage is for the situation 'all'.
    When A user says with at least _ shots faced, they mean that the column 'ongoal' has a value greater than or equal to that number

    The team table should only be used when a stat is being asked for an entire team. ie. "what team had the highest shooting percentage in the 2023-24 season." 
    If someone asks who lead a team in a stat, still use the individual tables. Only use this table for team wide stats. Other than that, it is the same as the pairs, skaters, and goalie tables. Follow the same rules as you would for those.

    It is very common that someone may ask for a statistic with at least a number of minutes played. This measn that the player, line, or pair must have played at least that number of minutes. This can be determined with the icetime column. 
    Reminder that this column is stored in seconds. Convert a minumum number of minutes to seconds by multiplying by 60. Use this for the SQL query.

    If someone asks for a top _ in a stat, return the highest _ number in that stat. 
    For example the top 10 lines in expected goals percentage. This means return the top 10 lines from linestats_regular_2024 in expected goals percentage.
    
    This is the same for defensive pairings. For example if someone asks for the expected goals percentage of the makar toews pairing, this should be interperated as the makar-toews pairing.
    Despite adding the dashes, keep the order of the names the same. So for the line example that would be Knies-Matthews-Marner or for the pairs example Makar-Toews
    This should look in the name column for the line specified. 

    If someone asks where a person, line, pairing, or team ranks in a certain stat, then they want to know where they are in that stat like a standing. 
    For example, if someone asks for where did Auston Matthews rank in goals in the 2022-23 season, the answer would be first since he had the most goals that year.
    return the ranking that they are in this stat. Thats what being asked for. Please also include the value for that stat. So for Auston Matthews in that example it would be ranked 1st with 69 goals

    If someone asks where a line ranks in expected goals percentage return where they are in a list sorted by the highest percentages. For example a pair would rank fifth NOT 60%. Return both of these, but make sure you return the ranking.
    
    You can find where a line or individual ranks in a stat using the RANK function in SQL. For questions asking for the ranking or a skater, line, pair, or line.

    For example if someone asks, Where does knies matthews marner rank for forward lines in expected goals percentage? the SQL query should be:

    'SELECT `rank`, xGoalsPercentage FROM (SELECT name, RANK() OVER (ORDER BY xGoalsPercentage DESC) AS `rank`, xGoalsPercentage FROM LineStats_regular_2024) AS ranked_data WHERE name LIKE '%Knies%' AND name LIKE '%Matthews%' AND name LIKE '%Marner%';

    If someone requests where a skater, line, pairing, or team ranks among _. This is asking for where they are in a list sorted by the stat they are asking for, where all the things in the list meet a certain condition. For example:
    Where does Makar-Toews rank in expected goals percentage among defense pairs with at least 150 minutes. Means where in the list of pairs with over 150 minutes do they rank in expected goals perecentage. 

    For lines, reminder that expected goals percentage is stored as xGoalsPercentage, and it stored as a decimal value. If someone asks for over 60% they mean that xGoalsPercentage is over 0.6

    If someone requests a current rank, where does __ rank in ___ stat. Use the 2024 tables.
    
    A user may request a list or table from the shots_data table. Give a list back that can be interperated to find the stat of the user query. So for example if you are prompted to return a table of shots for finding expected goals percentage, then find the table and include the xgoals column.
    Here is a data dictionary with correct titles for the shots_data table to help you return lists of shots: 
    shotID: Unique id for each shot
    homeTeamCode: The home team in the game. For example: TOR, MTL, NYR, etc
    awayTeamCode: The away team in the game
    season: Season the shot took place in. Example: 2009 for the 2009-2010 season
    isPlayoffGame: Set to 1 if a playoff game, otherwise 0
    game_id: The NHL Game_id of the game the shot took place in
    time: Seconds into the game of the shot
    period: Period of the game
    team: The team taking the shot. HOME or AWAY
    location: The zone the shot took place in. HOMEZONE, AWAYZONE, or Neu. Zone
    event: Whether the shot was a shot on goal (SHOT), goal, (GOAL), or missed the net (MISS)
    goal: Set to 1 if shot was a goal. Otherwise 0
    xCord: The X coordinate "North South" on the ice of the shot. Feet from red line.  -89 and 89 are the goal lines at each of the rink
    yCord: The Y coordinate  "East West" on the ice of the shot. The middle of the ice has a y-coordinate of 0
    xCordAdjusted: Adjusts the x coordinate as if all shots were at the right end of the rink. Usually makes the coordinate a positive number
    yCordAdjusted: Adjusts the y coordinate as if all shots were at the right end of the rink.
    homeTeamGoals: Home team goals before the shot took place
    awayTeamGoals: Away team goals before the shot took palce
    homeSkatersOnIce: The number of skaters on the ice for the home team. Does not count the goalie
    awaySkatersOnIce: The number of skaters on the ice for the away team. Does not count the goalie
    goalieNameForShot: The First and Last name of the goalie the shot is on.
    shooterPlayerId: The NHL player id of the skater taking the shot
    shooterName: The First and Last name of the player taking the shot
    xGoal: The probability the shot will be a goal. Also known as "Expected Goals"
    playerPositionThatDidEvent: The position of the player doing the shot. L for Left Wing, R for Right Wing, D for Defenceman, C for Centre.
    teamCode: The team code of the shooting team. For example, TOR, NYR, etc
    nhl_game_id: This is the unique identifier for each individual game the shot took place in. This number begins with the season, then has an indicator for season type, and then a number. More recent games, allways have a larger number.
    gameDate: a date when the shot took place. Repersented as year-month-day. For example, November 27th 2024 would be: 2024-11-27
    shooting_team_players: This is a list of the players on the ice for the shooting team at the time of the shot. They are listed as the full names seperated by a comma. Often times a players last name will be the only name given. Use like keyword in a SQL query.
    opposing_team_players: This is a list of the players on the ice for the opposing team at the time of the shot. They are listed as the full names seperated by a comma. Here is an example of what the column would have: "Nicolas Aube-Kubel, Sam Lafferty, Beck Malenstyn, Henri Jokiharju, Rasmus Dahlin"
    
    An example of a request for a shots_data table would be: 'Please return a list of shots from the shots_data table that contains only the columns and rows relavent to the query: What was the expected goals percentage for the Oilers between Jan 1st 2020 and Jan 10th 2020. Note today's date is _ '
    Here you would return a list of all shots between 2020-01-01 and 2020-01-10, where either the home or away team was the edmonton oilers. You would only need the columns that make it clear which team took the shots and teams that played. So include the teamCode and the xgoals column.
    
    If somone asks for a stat over the last _ number of games. First satisfy the conditions, and then return a list with only the _ greatest unique values for nhl_game_id.
    If somone asks for the number of goals over a stretch, its important to only report from the last 20 games. This means you cannot return only shots with goals, since this will only find games where the player scored. Remember that.
    In that case, just return all the shots taken by the player in each of the last 20 games. This will be put into a dataframe to determine the number, so its important to include every shot, and insure its only coming from the last 20 games. Even if he did not shoot in a game.

    When someone asks for the amount of shots, goals, expected goals, ect. And wants to use the shots_data table, return a list of ALL shots from the last n unique nhl_game_id values. ALL shots from the past 10 games. each game is identified with this id.

    If someone asks for a line's stat over a date range or in the last _ games, return all the shots where all three of the names are listed. Lines will often only include the last name when requested, the full name is listed in the shots_data table. Keep that in mind.

    If someone asks for a ranking using the shots_data table then return all the shots for all teams and players meeting the conditions so they can find a rankning.

    This may also require some thinking, for example, if someone asks for a stat 'in the month of march' return a list for all marches in the past seasons. But if someone says this march, take the year from the current date thats provided in the question and ask for that march.
    If no year is provided, use the current year passed in the date.

    For queries using the last _ games, Here is a sample sql query to help generate one that will work with the version of MySQL used in this database:
    "sELECT shooterName, teamCode, goal, shots_data.nhl_game_id, shotID FROM nhlstats.shots_data JOIN (sELECT nhl_game_id FROM shots_data WHERE shooterName = 'shooter name' GROUP BY nhl_game_id ORDER BY nhl_game_id DESC LIMIT game number) recent_games ON shots_data.nhl_game_id = shots_data.nhl_game_id WHERE shooterName = 'shooter name';"
    This would be the query for the shots for a player in the last _ number of games, where game number is the number of games asked about and shooter name is the player asked about.
    Also reminder: MySQL does not support using LIMIT inside a subquery within an IN clause.

    A user may also request a list of gameID's that meet a certain condition. This may mean finding the destinct nhl_game_id values that meet a certain shot condition, for example, games where 'Connor Mcdavid scored' would be destinct nhl_game_id values for shots_data where there were connor mcdavid goals.
    Use shots_data if the user requests a a list of gameIDs given a condition about a player, or very specific information like where the Montreal Canadians scored in the second period ect. Use game_logs for TEAM level information that is about the entire game. 

    
    DO NOT INCLUDE ``` in the response. Do not include a period at the end of the response.
    Question: {question}
    SQL Query:
    """

    prompt = ChatPromptTemplate.from_template(template)


    # def extract_sql_query(response):
    #     """Extract only the first SQL query and clean any formatting issues."""
    #     print("RAW LLM OUTPUT:\n", response)  # Debugging step

    #     # Strip unnecessary whitespace and formatting
    #     response = response.strip().strip("`")

    #     # Use regex to extract the first valid SQL query
    #     matches = re.findall(r"(?i)(SELECT|INSERT|UPDATE|DELETE|WITH)\s+.*?(;|$)", response, re.DOTALL)

    #     if matches:
    #         return matches[0][0] + response[len(matches[0][0]):].strip()  # Return the first match
    #     else:
    #         return response.strip()  # Fallback to raw response if no match found



    sql_chain = (
        RunnablePassthrough.assign(schema=lambda _: get_table_schema(db))
        | prompt
        | llm
        | StrOutputParser()
        |(lambda sql_query: print("Generated SQL Query:", sql_query) or sql_query) 
        #|(lambda output: extract_sql_query(output)) 
    )
    return sql_chain

def get_chain(db, llm):
    def run_query(query, db):
        return run_query_mysql(query, db)
    
    #database functions. Get information from the databases to be used in the chain
    def get_table_schema(db):
        relevent_tables = ['SkaterStats_regular_2024', 'GoalieStats_regular_2024', 'LineStats_playoffs_2024', 'PairStats_regular_2024', 'teamstats_regular_2024']
        return get_table_info(db, relevent_tables) #return the schema of the first table in the list


    sql_chain = get_sql_chain(db, llm)

    #print(sql_chain.invoke({"question": "How many goals did William Nylander score in the 2018 playoffs"}))
    #print(sql_chain.invoke({"question": "How many goals did Sidney Crosby score in the 2023 regular season?"})) #Test the first chain generating sql query

    template = """
    Based on the table schema below, quesiton, sql query, and sql response, write a natural language response to the user question.
    {schema}


    Quesiton: {question}
    SQL Query: {query}
    SQL Response: {response}
    Please note that  Save percentage should be presented as a decimal value NOT AS A PERCENTAGE, for example 0.916. There should NEVER be percentage sign. It should have three decimal places.
    So 91.6% would be 0.916. Never return with a percent sign for a goalie. Allways use a decimal value. NEVER use the form 91.6%. ONLY USE 0.916. This is counter intuitive but it is important convention.
    Do this only for save percentage. All other stats that are percentages are fine to return as a percentage. Use decimal only for save percentage.

    Note that if the question asks for a rank or where does something rank among _ include the simple number along with the stat. 
    For example someone asks where a line ranks in expected goals percentage return where they are in a list sorted by the highest percentages. For example a pair would rank fifth. The percentage is 60%. Return both of these, but make sure you return the ranking.
    If a user requests a record, find the number of regulation losses by substracting wins and overtime losses from the total games. Records are presented as Wins - Regulation losses - overtime losses. For example 3-2-1.
    """
    prompt = ChatPromptTemplate.from_template(template)

    full_chain = (
        RunnablePassthrough.assign(query = sql_chain).assign(schema = lambda _: get_table_schema(db)).assign(response=lambda variables: run_query(variables["query"], db))
        | prompt
        | llm
        | StrOutputParser()
    )

    #print(full_chain.invoke({"question": "During the 2023 regular season, what player led the NHL in on ice expected goals for percentage at even strength with a minimum of 100 minutes played. What was that expected goals percentage. How many goals did this player have? What team did he play for?"})) # Test the second chain generating natural language response

    #print(full_chain.invoke({"question": "What player lead the kings in expected goals percentage at even strength with a minimum of 100 minutes during the 2023 regular season? What was that percentage and how many assists did this player have?"})) # Test the second chain generating natural language response
    #print(full_chain.invoke({"question": "who lead the toronto maple leafs in 5 on 5 expected goals percentage with at least 100 minutes played in the 2023 regular season?"}))

    #print(full_chain.invoke({"question": "How many goals did William Nylander score in the 2018 playoffs"}))

    #print(full_chain.invoke({"question": "Who had the highest goals saved above expected in the 2023 regular season"}))

    #print(full_chain.invoke({"question": "What pairing had the highest expected goals percentage with at least 100 minutes in 2023?"}))

    return full_chain
    