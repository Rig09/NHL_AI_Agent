from langchain import hub
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from chains.stats_sql_chain import get_chain, get_sql_chain
from figure_generation.shot_map_plotting import goal_map_scatter_get, shot_map_scatter_get, shot_heat_map_get, goal_heat_map_get, xg_heat_map_get
from chains.rag_chains import get_cba_information, get_rules_information
from chains.bio_info_chain import get_bio_chain
from pydantic import BaseModel, Field
from chains.nhl_api_chain import query_nhl
from datetime import datetime, date
from chains.dated_stats import get_stats_by_dates, get_stats_ngames
from stat_hardcode.xg_percent import ngames_player_xgpercent, date_player_xgpercent, ngames_team_xgpercent, date_team_xgpercent,ngames_line_xgpercent, date_line_xgpercent
from api_tools.career_totals import get_nhl_player_career_stats
from api_tools.api_endpoints import get_nhl_standings, nhl_schedule_info_by_date
from stat_hardcode.game_information import game_information
from stat_hardcode.team_record import team_record
from figure_generation.player_cards import fetch_player_card

class goal_map_scatter_schema(BaseModel):
    conditions : str = Field(title="Conditions", description="""The conditions to filter the data by. This should be a natural language description of the data for the scatterplot. This should include information like the team, player, home or away, ect.
                              This description should not include the strength or the season_type. Do not include that information in this field. This field will be used to create a table of data relevent to the scatterplot or heatmap.
                                For example, if a user requested a heatmap of leafs powerplay shots in the 2023-24 season, the conditions would be something like: Shots taken by players on the Toronto Maple Leafs""")
    season_lower_bound: int = Field(title="Season_lower_bound", description="""The first season in the range of seasons to generate the goal map scatter plot for. 
                                    Often a season can be refered to using two different years since it takes place on either side of new years,  like 'in the 2020-2021 season', 
                                    pass the first year as the argument. Another way this could be done is by only using the last two numbers of the second year. For example 2020-21 means pass '2020'
                                    Pass this as ONLY the integer value. So if the user asks for the 2022 season. Pass the argument '2022'. That said, if someone asks for a stat in the 2023 playoffs, they are refering to the 2022-23 season. So use 2022 as the season.
                                    DO NOT PASS 'Season 2022' Pass '2022'. When a range of seasons is provided like, 'from the 2015 to 2024 season generate a scatterplot' 
                                    This is the lower bound of the range. ie. the older year should be this value. If the user says "this season" this is refering to the 2024 season. Use 2024 in this case.""")
    season_upper_bound: int = Field(title="Season_upper_bound", description="""The second season in the range of seasons to generate the goal map scatter plot for. 
                                    If only a single season is provided like 'generate a scatterplot for the 2022-23 season' then this value should be the same as season_lower_bound. 
                                    If there is a range of seasons in the request, then this should be the newest year. For example if someone asks 'generate a scatterplot for goals from the 2017-2023 seasons' 
                                    then this would take the value 2024. If the user says "this season" this is refering to the 2024 season. Use 2024 in this case. Someone may also say, 'generate a scatterplot from 2017-18 to 2022-23. Then the value of this would be 2022. Allways pass the fist year 
                                    if the season is given as multiple years. Interperate whether a range of seasons or single season is being requested. If it is a range, the upper bound should be this value.
                                    If it is a single, this value should be the same as lower_bound_season. Also note that if someone asks for a stat that is in the 2024 playoffs. This is actually from the season 2023-24.
                                    DO NOT PASS 'Season 2022' Pass '2022'""")
    season_type: str = Field(title="Season Type", description="""The type of season this should be past as: 'regular', 'playoffs', or 
                             'all'. Default to passing the word 'regular' if it is not specified. The playoffs can also be called the
                              postseason, this should be passed as playoffs""")
    situation: str = Field(title="Situation", description="The situation which can be on the powerplay, even strength," 
                           "shorthanded, or all situations depending on the number of players on the ice. Default to all situations if not specified. to generate the goal map scatter plot for. Pass these situations as 5on4 for powerplay, 4on5 for shorthanded, 5on5 for even strength, and all for all situations")

class rag_args_schema(BaseModel):
    query: str = Field(..., description='The query to be executed by a RAG system. This will be fed into a function which will provide an answer to the query based on text files relevant to the query')

class NHLAPI_schema(BaseModel):
    query: str = Field(..., description='The query to be executed by an API chain. This will process a natural language query and use the NHL api to return an answer. The query should be asking for current information about the NHL, such as scheduling information.'
    'The query can also ask about historic data, current scores and more.')

class dated_stats_schema(BaseModel):
    natural_language_query: str = Field(..., description="""This should be a natural language description of the question the person is asking, if the tool is invoked, this should be the question that was asked of the agent.'
    'This should allways include a natural language description of a condition on the dates. Like for example 'in the month of march' or 'over the last month' """)

class ngames_stats_schema(BaseModel):
    natural_language_query: str = Field(..., description="""This should be a natural language description of the question the person is asking, if the tool is invoked, this should be the question that was asked of the agent.'
    'This should allways include a natural language description of a condition on the games. This is either using game numbers, like 'between games 30 and 40' or 'in the last 5 games' """)    

class ngames_xg_percent_schema(BaseModel):
    player_name: str = Field(..., description= 'The name of the player for which the request is being made')
    game_number: int = Field(..., description= "The number of games being asked about. So if someone says what is Connor Mcdavid's expected goals percentage in the last 10 games. Then this would take the value of 10.")
    strength: str = Field(title="Strength", description="""The strength of the game. This refers to the number of players on the ice for each time. For xg percents, this can either be 'even strength'(aka 5 on 5, or ev, or 5v5) or 'all'
                          Only invoke with one of those two. If it is not specified, default to 'even strength'""")
class ngames_xg_team_percent_schema(BaseModel):
    teamCode: str = Field(..., description= """The team code for the team which is being asked about, Note for the team codes: Anaheim Ducks -> ANA, Arizona Coyotes -> ARI, Boston Bruins -> BOS, 
                          Buffalo Sabres -> BUF, Calgary Flames -> CGY, Carolina Hurricanes -> CAR, Chicago Blackhawks -> CHI, Colorado Avalanche -> COL, Columbus Blue Jackets -> CBJ, 
                          Dallas Stars -> DAL, Detroit Red Wings -> DET, Edmonton Oilers -> EDM, Florida Panthers -> FLA, Los Angeles Kings -> LAK, Minnesota Wild -> MIN, 
                          Montreal Canadiens -> MTL, Nashville Predators -> NSH, New Jersey Devils -> NJD, New York Islanders -> NYI, New York Rangers -> NYR, Ottawa Senators -> OTT,
                           Philadelphia Flyers -> PHI, Pittsburgh Penguins -> PIT, San Jose Sharks -> SJS, Seattle Kraken -> SEA, St. Louis Blues -> STL, Tampa Bay Lightning -> TBL, 
                          Toronto Maple Leafs -> TOR, Vancouver Canucks -> VAN, Washington Capitals -> WSH, Winnipeg Jets -> WPG. Also imply nicknames, like The jets, leafs, habs, sharks, ect.""")
    game_number: int = Field(..., description= "The number of games being asked about. So if someone says what is the Jets expected goals percentage in the last 10 games. Then this would take the value of 10.")
    strength: str = Field(title="Strength", description="""The strength of the game. This refers to the number of players on the ice for each time. For xg percents, this can either be 'even strength'(aka 5 on 5, or ev, or 5v5) or 'all'
                          Only invoke with one of those two. If it is not specified, default to 'even strength'""")

class date_xg_percent_schema(BaseModel):
    player_name: str = Field(..., description= 'The name of the player for which the request is being made')
    start_date: date = Field(..., description= "The start of the date range being asked about. So if someone says what is Connor Mcdavid's expected goals percentage Since January 1st. Then this would take the value of 2024-01-01.")
    end_date: date = Field(..., description= "The start of the date range being asked about. So if someone says what is Connor Mcdavid's expected goals percentage from January 1st to January 10th. Then this would take the value of 2024-01-10. If someone says since _ or doesnt give an end date use todays date")
    strength: str = Field(title="Strength", description="""The strength of the game. This refers to the number of players on the ice for each time. For xg percents, this can either be 'even strength'(aka 5 on 5, or ev, or 5v5) or 'all'
                          Only invoke with one of those two. If it is not specified, default to 'even strength'""")
class date_team_xg_percent_schema(BaseModel):
    teamCode: str = Field(..., description= """The team code for the team which is being asked about, Note for the team codes: Anaheim Ducks -> ANA, Arizona Coyotes -> ARI, Boston Bruins -> BOS, 
                          Buffalo Sabres -> BUF, Calgary Flames -> CGY, Carolina Hurricanes -> CAR, Chicago Blackhawks -> CHI, Colorado Avalanche -> COL, Columbus Blue Jackets -> CBJ, 
                          Dallas Stars -> DAL, Detroit Red Wings -> DET, Edmonton Oilers -> EDM, Florida Panthers -> FLA, Los Angeles Kings -> LAK, Minnesota Wild -> MIN, 
                          Montreal Canadiens -> MTL, Nashville Predators -> NSH, New Jersey Devils -> NJD, New York Islanders -> NYI, New York Rangers -> NYR, Ottawa Senators -> OTT,
                          Philadelphia Flyers -> PHI, Pittsburgh Penguins -> PIT, San Jose Sharks -> SJS, Seattle Kraken -> SEA, St. Louis Blues -> STL, Tampa Bay Lightning -> TBL, 
                          Toronto Maple Leafs -> TOR, Vancouver Canucks -> VAN, Washington Capitals -> WSH, Winnipeg Jets -> WPG. Also imply nicknames, like The jets, leafs, habs, sharks, ect.""")
    start_date: date = Field(..., description= "The start of the date range being asked about. So if someone says what is the Habs expected goals percentage Since January 1st. Then this would take the value of 2024-01-01.")
    end_date: date = Field(..., description= "The start of the date range being asked about. So if someone says what is Oiler's expected goals percentage from January 1st to January 10th. Then this would take the value of 2024-01-10. If someone says since _ or doesnt give an end date use todays date")
    strength: str = Field(title="Strength", description="""The strength of the game. This refers to the number of players on the ice for each time. For xg percents, this can either be 'even strength'(aka 5 on 5, or ev, or 5v5) or 'all'
                          Only invoke with one of those two. If it is not specified, default to 'even strength'""")
class date_lines_xg_percent_schema(BaseModel):
    player_one: str = Field(..., description= 'The name of the first player for which the request is being made')
    player_two: str = Field(..., description= 'The name of the second player for which the request is being made')
    player_three: str = Field(..., description= """The name of the third player for which the request is being made. Somtimes a request will be made for only two players. For this request it should pass 'None'""")
    start_date: date = Field(..., description= "The start of the date range being asked about. So if someone says what is Connor Mcdavid's expected goals percentage Since January 1st. Then this would take the value of 2024-01-01.")
    end_date: date = Field(..., description= "The start of the date range being asked about. So if someone says what is Connor Mcdavid's expected goals percentage from January 1st to January 10th. Then this would take the value of 2024-01-10. If someone says since _ or doesnt give an end date use todays date")

class ngames_lines_xg_percent_schema(BaseModel):
    player_one: str = Field(..., description= 'The name of the first player for which the request is being made')
    player_two: str = Field(..., description= 'The name of the second player for which the request is being made')
    player_three: str = Field(..., description= """The name of the third player for which the request is being made. Somtimes a request will be made for only two players. For this request it should pass 'None'""")
    game_number: int = Field(..., description= "The number of games being asked about. So if someone says what is the Jets expected goals percentage in the last 10 games. Then this would take the value of 10.")

class game_information_schema(BaseModel):
    game_ids: list[int] = Field(title="Situation", description="This is a list of the game_ids that the information is needed about. Invoke the stats tool to find these given the user conditions. Find the gameids and then invoke this function to find information about the games")
    situation: str = Field(title="Situation", description="The situation which can be on the powerplay, even strength," 
                           "shorthanded, or all situations depending on the number of players on the ice. Default to all situations if not specified. to generate the goal map scatter plot for. Pass these situations as 5on4 for powerplay, 4on5 for shorthanded, 5on5 for even strength, and all for all situations")

class player_card_schema(BaseModel):
    player_name: str = Field(..., description= 'The name of the player for which the request is being made')
    season: list[int] = Field(..., description= """The seasons for which the request is being made. This should be a list of integers. For example [2024, 2023] for the 2024 and 2023 seasons.
                              If someone says for the last _ seasons, then this should be a list of the last _ seasons. For example if someone says for the last 3 seasons, then this should be [2024, 2023, 2022].
                              If someone says for the last _ years, then this should be a list of the last _ seasons. For example if someone says for the last 3 years, then this should be [2024, 2023, 2022]. This can also be a list with only a single season.
                              If someone does not specify a season, or they ask for career stats then this should be an empty list. This will let the tool know to get the career statss since 2015. Make sure its an empty list given for this scenario.
                             If somsone says 'this season' give the list [2024]""")
# Helper function to create wrappers for tools
def create_tool_wrapper(func, vector_db):
    def wrapper(query: str):
        return func(vector_db, query)
    return wrapper

def get_agent(db, rules_db, cba_db, llm):
    
    todays_date = date.today()

    @tool(args_schema=goal_map_scatter_schema)
    def goal_map_scatter(conditions, season_lower_bound =2024, season_upper_bound=2024, season_type = "regular", situation = "all"):
        """Returns a scatterplot of the goals scored by a player or team or any other conditins specifiedin a given situation, season type and range of seasons. 
        The lower bound and upper bound of the range are the same if a single season is requested. Otherwise pass the bounds of the range.
        if a situation is not provided, we will assume the situation to be all situations
        if a season type is not provided, we will assume the season type to be regular season"""
        goal_map_scatter_get(db, llm, sql_chain, conditions, season_lower_bound, season_upper_bound, situation, season_type)
        return "Goal map scatter plot generated successfully"

    @tool(args_schema=goal_map_scatter_schema)
    def shot_map_scatter(conditions, season_lower_bound =2024, season_upper_bound=2024, season_type = "regular", situation = "all"):
        """Returns a scatterplot of the shots by a  player or team or any other conditins specified in a given situation, season type and range of seasons. 
        It is the same as goal_map_scatter but for shots. It uses the same schema and arguments.
        if a situation is not provided, we will assume the situation to be all situations
        if a season type is not provided, we will assume the season type to be regular season"""
        shot_map_scatter_get(db, llm, sql_chain, conditions, season_lower_bound, season_upper_bound, situation, season_type)
        return "Goal map scatter plot generated successfully"

    @tool(args_schema=goal_map_scatter_schema)
    def shot_heatmap_getter(conditions, season_lower_bound =2024, season_upper_bound=2024, season_type = "regular", situation = "all"):
        """Returns a heatmap of the shots by the player or team or any other conditins specified in a given situation, season type and range of seasons. 
        Like goal_map_scatter it uses the same schema and arguments.
        if a situation is not provided, we will assume the situation to be all situations
        if a season type is not provided, we will assume the season type to be regular season
        if the user requests a heatmap of shots, or a shot heatmap, it should invoke this tool"""
        shot_heat_map_get(db, llm, sql_chain, conditions, season_lower_bound, season_upper_bound, situation, season_type)
        return "Shot heatmap generated successfully"

    @tool(args_schema=goal_map_scatter_schema)
    def goal_heatmap_getter(conditions, season_lower_bound =2024, season_upper_bound=2024, season_type = "regular", situation = "all"):
        """Returns a heatmap of the goals scored by the player or team or any other conditins specified, in a given situation, season type and range of seasons. 
        Like goal_map_scatter it uses the same schema and arguments.
        if a situation is not provided, we will assume the situation to be all situations
        if a season type is not provided, we will assume the season type to be regular season
        if the user requests a heatmap of goals, or a goal heatmap, it should invoke this tool"""
        goal_heat_map_get(db, llm, sql_chain, conditions, season_lower_bound, season_upper_bound, situation, season_type)
        return "Goal heatmap generated successfully"
    
    @tool(args_schema=goal_map_scatter_schema)
    def xg_heatmap_getter(conditions, season_lower_bound =2024, season_upper_bound=2024, season_type = "regular", situation = "all"):
        """Returns a heatmap of the average expected goals in different locations by the player or team or any other conditins specified, in a given situation, season type and range of seasons. 
        Like goal_map_scatter it uses the same schema and arguments.
        if a situation is not provided, we will assume the situation to be all situations
        if a season type is not provided, we will assume the season type to be regular season
        if the user requests a heatmap of expected goals, or an xg heatmap or a expected goal heatmap, or something similar it should invoke this tool"""
        xg_heat_map_get(db, llm, sql_chain, conditions, season_lower_bound, season_upper_bound, situation, season_type)
        return "Expected Goal heatmap generated successfully"

    @tool(args_schema=rag_args_schema)
    def rule_getter(query: str):
        """Returns the relevant rule information based on the query. This tool should be invoked using the rules_db as the vector_db field which is
        passed into the getter function.Any query about a hypothetical situation in hockey should use this tool
        For example: 'what happens if...', preceeded by an event that could occur in a game.
        Use this tool when the user asks about an NHL rule. For example 'can you kick a puck into 
        the net' or 'what is offside'. This function will also return the rule numbers referenced. 
        Please keep those in the response.
        When THIS TOOL IS CALLED KEEP THE SPECIFIC RULE NUMBER IN THE RESPONSE 
        for example at the end of a response it could say (RULE 48.2) keep that rule refrence"""
        return get_rules_information(rules_db, llm, query)

    @tool(args_schema=rag_args_schema)
    def cba_getter(query: str):
        """Returns the relevant CBA information based on the query. This tool should be invoked using the cba_db as the vector_db field which is 
        passed into the getter function. This tool should be used to answer any queries about the buissness, salary cap, or salary structure in the NHL. Any question asking how 
        an aspect of the NHL works that is not a gameplay rule should use this tool. This includes question about revenue, escrow, or any other buissness information about the NHL. 
        This includes hypothetical questions like 'what happens if a team goes over the cap with bonus'.
        This also includes information like information about revenue, profit, or any other buissness information about the NHL. 
        If a specific component of the CBA is refrenced keep that in the response. For example the return may say per CBA Section 50.12(g)-(m). Keep that in the final response"""
        return get_cba_information(cba_db, llm, query)
    
    @tool(args_schema=NHLAPI_schema)
    def nhl_api_question(query:str):
        """
        This tool interacts with the NHL API to get information on a couple of different hockey related queries. It can get current data, for example the schedule of todays games, or current scores
        It can also get historical data, like the all time leaders in a certain stat like "the all time leader in goals" for example. It can also return the schedule or scores for a specific date.
        The tool should also be invoked about stats from outside the scope of the Statistic Getter. So any stat that is from before the 2015 season should invoke this tool. Otherwise use the other tool.
        """
        return query_nhl(llm, query)
    
    @tool(args_schema=dated_stats_schema)
    def dated_stat_getter(natural_language_query:str):
        """
        This tool should be invoked whenever a user has a question about a stat about an individual that involves a date. This tool is only for skaters, lines, and goalies. DO not use it for team stats. An example us is if a user asks about goals this march for Connor Mcdavid, 
        or over the past 30 days who has the most assists. Any statistical query about stats that is has any relation to dates should invoke this tool. Only counting stats should invoke this tool. So if someone asks for expected goals percentage, corsi, possesion, ect. Do not invoke this tool.
        If a user says something like this calendar year, or this month, or this week. DO NOT INFER what that means. Pass that information to this tool, it has the context of todays date.
        """
        return get_stats_by_dates(llm, db, sql_chain, natural_language_query, todays_date)
    
    @tool(args_schema=ngames_stats_schema)
    def n_games_stat_getter(natural_language_query:str):
        """
        This tool should be invoked whenever a user has a question about a stat using a range of games. For example if a user asks about goals in the last 5 games. Or between game 40 and 50. ect.
        Any statistical query about asking about a range of games, should invoke this tool. Only counting stats should invoke this tool. So if someone asks for expected goals percentage, corsi, possesion, ect. Do not invoke this tool
        """
        return get_stats_ngames(llm, db, sql_chain, natural_language_query)
    
    @tool(args_schema=ngames_xg_percent_schema)
    def n_games_xgpercent_getter(player_name, game_number, strength: str = 'even strength'):
        """
        This tool should be invoked when someone asks for a player's expected goals percentage over the last _ number of games. This is the only use. It will return the percentage value as a decimal. Translate this as a percentage.
        """
        return ngames_player_xgpercent(db, player_name, game_number, strength)
    
    @tool(args_schema=ngames_xg_percent_schema)
    def n_games_team_xgpercent_getter(teamCode, game_number, strength: str = 'even strength'):
        """
        This tool should be invoked when someone asks for a team's expected goals percentage over the last _ number of games. This is the only use. It will return the percentage value as a decimal. Translate this as a percentage.
        """
        return ngames_team_xgpercent(db, teamCode, game_number, strength)

    @tool(args_schema=date_xg_percent_schema)
    def date_xg_percent_getter(player_name, start_date, end_date = todays_date, strength: str = 'even strength'):
        """
        This tool should be invoked when someone asks for a player's expected goals percentage over a certain date range.
        This is the only use. It will return the percentage value as a decimal. Translate this as a percentage.
        """
        return date_player_xgpercent(db, player_name, start_date, end_date, strength)
    
    @tool(args_schema=date_team_xg_percent_schema)
    def date_team_xg_percent_getter(teamCode, start_date, end_date = todays_date, strength: str = 'even strength'):
        """
        This tool should be invoked when someone asks for a team's expected goals percentage over a certain date range.
        This is the only use. It will return the percentage value as a decimal. Translate this as a percentage.
        """
        return date_team_xgpercent(db, teamCode, start_date, end_date, strength)
    
    @tool(args_schema=date_lines_xg_percent_schema)
    def date_lines_xg_percent_getter(player_one, player_two, start_date, end_date, player_three = 'None'):
        """
        This tool should be invoked when the user asks for a line or pairings expected goals percentage over a specified date range. 
        Defensive pairings only have two player, if someone asks for a line or pairing with only two players, simply pass the defualt 'None' to player_three
        This is the only use. The tool will return a decimal, convert this to a percentage.
        """
        return date_line_xgpercent(db, player_one, player_two, player_three, start_date, end_date)
    
    @tool(args_schema=ngames_lines_xg_percent_schema)
    def ngames_lines_xg_percent_getter(player_one, player_two, game_number, player_three = 'None'):
        """
        This tool should be invoked when someone asks for a player's expected goals percentage over the last _ number of games. This is the only use. It will return the percentage value as a decimal. Translate this as a percentage.
         Defensive pairings only have two player, if someone asks for a line or pairing with only two players, simply pass the defualt 'None' to player_three
        """
        return ngames_line_xgpercent(db, player_one, player_two, player_three, game_number)
    @tool
    def getDate():
        """
        returns the current date. This could be useful if a user asks a question that requires context about the date. 
        This allows you to pass to other tools and infer the meaning if the dates given are ambiguous and require todays date to imply them. Use this tool to get extra information about a date.
        For example, if the user says 'since march' Then use this tool to find the current date so you can pass the correct year to the tool thats needed. Allways invoke when someone refrences a month and does not provide a year.
        This is important context to use for other tools.
        """
        return todays_date
    
    @tool
    def player_career_stats(player_name: str):
        """
        Invoke this tool to find the career totals for a given player based on the players name. This will return the career totals for a player in the following stats:
        assits, average time on ice (avgToi), game winning goals (gameWinningGoals), games played (gamesPlayed), goals, overtime goals (otGoals), penalty minutes (pims), plus minus (plusMinus), points, powerplay goals (powerPlayGoals),
        power play points (powerPlayPoints), shooting percentage (shootingPctg) (this is stored as a decimal, convert to percentage), shorthanded goals (shorthandedGoals), shorthanded points (shorthandedPoints), and shots.
        It will return all of those stats for both the regular season and playoffs. It will give full career totals for those stats. If anyone asks for the amount of any of those stats a player has in there career either in the playoffs or regular season, invoke this tool.
        If someone does not specify give the amount of regular season of a stat, and the playoff amounts. If someone asks for a players career totals, and doesnt specify the stat, show all of these stats.
        """
        return get_nhl_player_career_stats(db, player_name)

    @tool(args_schema=game_information_schema)
    def get_game_information(game_ids: list[int], situation: str = 'all'):
        """
        This tool returns all the information about games given a list of gameIDs and situation being asked about. It should be invoked with a list of game ids and a situation, and will return all sorts of information about each game in the specified situation.
        This includes a teams expected goals percentage, corsi for, goals for, ect. Interperate this information to provide the user an answer to his query.
        This tool should NOT be used for team records or for counting win/loss/overtime loss. ONLY USE THIS TOOL FOR MORE IN DEPTH STATS. For example expected goals percentage, goals for, corsi for, ect. That is what it returns.
        DO NOT USE FOR TEAMR RECORDS. DO NOT EVER USE FOR TEAM RECORDS.
        """
        return game_information(db, situation, game_ids)
    @tool
    def get_record(query: str):
        """
        This tool should be invoked to return the record of a team given a certain set of conditions. It will return the wins, total games, and overtime losses. The final product should be presented as follows:
        wins-regulationLosses-OverTimeLosses. For example: 3-2-1. or 10-5-2. Note that you find regulation losses by taking the toal games and subtracting the other two values. Always invoke this tool for any question about a teams record.
        Simply pass it the natural language description of the conditions for the record. Add context to the date if it is needed. For example adding the year to a date using the getDate tool.
        This tool will return a string value that describes the three outputs. Interperate this and return a natural language response to the user. Dont invoke this tool using a date without year information.
        """
        return team_record(db, llm, query)
    @tool(args_schema=player_card_schema)
    def player_card_getter(player_name: str, season: list[int] = []):
        """
        This tool should be invoked to get a player card for a given player. It will return the player card for the player in the specified seasons. 
        If no seasons are specified, it will return the players career totals. If someone asks for a player card, invoke this tool.
        If no seasons are specified, invoke this tool with an empty list. If someone asks for a player card, and they specify a season, pass that season as a list of integers.
        For example if someone asks for a player card for Connor Mcdavid in the 2024 season, pass the list [2024]. If someone asks for a player card for Connor Mcdavid in the 2023 and 2024 seasons, pass the list [2023, 2024].
        Also invoke this tool if someone asks for a career summary, or season summary for a player.
        """
        fetch_player_card(db, player_name, season)
        return "Player card generated successfully"
    @tool
    def get_standings(date: date):
        """
        This tool should be invoked to get the standings for the NHL on a given date. It will genertate a figure with the standings for the NHL on that date, including the wins, losses, and overtime losses for each team.
        The tool will return a message saying that the standings have been generated successfully. If someone does not specify a date then imply and use todays date. If a date is ambigious look for todays date to imply context.
        Its important to pass the correct date. 
        """
        get_nhl_standings(date)
        return "Standings generated successfully"

    @tool
    def get_schedule_for_date(date: date):
        """
        This tool should be invoked to get the schedule for the NHL on a given date. It will return a dictionary with informations on all the games on that date. 
        Please use this if the user asks for schedule information about a certain date in the NHL. Use a tool to get context about the date if its unclear. 
        If no date is provided, use the getDate tool to get the current date. Also Add a note in the response that if there have been reschedules or changes to the schedule, this may not be accurate.
        """
        return nhl_schedule_info_by_date(date)
    chain = get_chain(db, llm)

    bio_chain = get_bio_chain(db, llm)

    sql_chain = get_sql_chain(db, llm)

    memory = ConversationBufferMemory(
        memory_key="chat_history", return_messages=True)

    # # Wrap the rule_getter and cba_getter functions to keep signature intact
    # rule_getter_wrapped = create_tool_wrapper(rule_getter, rules_db)
    # cba_getter_wrapped = create_tool_wrapper(cba_getter, cba_db)

    tools = [
        goal_map_scatter,
        shot_map_scatter,
        rule_getter,
        cba_getter,
        shot_heatmap_getter,
        goal_heatmap_getter,
        xg_heatmap_getter,
        nhl_api_question,
        dated_stat_getter,
        n_games_stat_getter,
        n_games_xgpercent_getter,
        n_games_team_xgpercent_getter,
        date_xg_percent_getter,
        date_team_xg_percent_getter,
        getDate,
        ngames_lines_xg_percent_getter,
        date_lines_xg_percent_getter,
        player_career_stats,
        #get_game_information,
        get_record,
        player_card_getter,
        get_standings,
        get_schedule_for_date,
        Tool(
            name="StatisticsGetter",
            func=lambda input, **kwargs: chain.invoke({"question": input}),
            description="""Useful when you want statistics about a player, line, defensive pairing, or goalie. The tool should not be invoked with an sql query. 
                            It should be invoked with a natural language question about what statistics are needed to answer the user query.
                            It will generate and perform an sql query on data from the 2015-2024 NHL seasons. Do not invoke this tool if it is outside the season range 2015-2024
                            Note someone may refer to a season using two years. So the 2024-25 season also counts and should be invoke this tool. 
                            Questions about current statstics should use the 2024 season. If a question about that is asked, it will return a string with the answer to that question in natural language.
                            somtimes for a ratio statistic the tool will return too names if a minumum minutes or shots against is not given. Return both, unless they are the same person. 
                            In the special case that the user asks for save percentage, despite the name, the tool will return a decimal. Keep that value as is. 
                            If the tool returns a percentage or decimal, never change it. The tool knows correct conventions.
                            If a user asks you to evaluate a player you can use this tool to get common statistics to measure performance. These include: goals, points, assists, expected goals percentage, ect.
                            This tool should be invoked to determine the rank of a line, pair, skater, or team in a statistic. Include the ask for this ranking when invoking this tool.
                            For example: if the user asks where does the Makar-Toews pairing rank in expected goals percentage, YOU MUST PASS THAT YOU WOULD LIKE THE RANKING. Pass: ranking for Makar Toews pairing in expected goals percentage.
                            Also infer similair meanings to what rank, like what place are they in, or where are they in the league ect. pass those asking for a ranking.
                            When there is an ambigious date argument, like 'since January' where the year is not provided, use the date tool to pass the year when you invoke this tool.
                            Invoke this tool for some game queries around things like "when was the last time 2 powerplay goals for the oilers happened in a game", or in how many games did _ happen this season ect."""
        ),
        Tool(
            name="Player_BIO_information",
            func=lambda input, **kwargs: bio_chain.invoke({"question": input}),
            description="""Useful when you want BIO information about a player, including position, handedness, height, weight, Nationality, Birthday, and team.
                            The tool should not be invoked with an sql query. It should be invoked with a natural language question about what statistics are needed to answer the user query."""
        )
    ]
    # TODO: Add the tools for the goal map scatter and shot map scatter
    
    # Pull the prompt template from the hub
    prompt = hub.pull("hwchase17/openai-tools-agent")

    # Create the ReAct agent using the create_tool_calling_agent function
    agent = create_tool_calling_agent(
        llm=llm,  # Language model to use
        tools=tools,  # List of tools available to the agent
        prompt=prompt,  # Prompt template to guide the agent's responses 
    )

    # Create the agent executor
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,  # The agent to execute
        tools=tools,  # List of tools available to the agent
        handle_parsing_errors=True,  # Handle parsing errors gracefully
        memory=memory,
    )
    return agent_executor