from langchain import hub
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from chains.stats_sql_chain import get_chain
from shot_maps.shot_map_plotting import goal_map_scatter_get, shot_map_scatter_get, shot_heat_map_get, goal_heat_map_get, xg_heat_map_get
from chains.rag_chains import get_cba_information, get_rules_information
from chains.bio_info_chain import get_bio_chain
from pydantic import BaseModel, Field

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
    #vector_db: Any = Field(..., description='A vector database for the RAG chain to interact with. This should be passed to the tool from the rules_db or cba_db depending on the tool used')
    query: str = Field(..., description='The query to be executed by a RAG system. This will be fed into a function which will provide an answer to the query based on text files relevant to the query')

# Helper function to create wrappers for tools
def create_tool_wrapper(func, vector_db):
    def wrapper(query: str):
        return func(vector_db, query)
    return wrapper

def get_agent(db, rules_db, cba_db, llm):

    @tool(args_schema=goal_map_scatter_schema)
    def goal_map_scatter(conditions, season_lower_bound =2024, season_upper_bound=2024, season_type = "regular", situation = "all"):
        """Returns a scatterplot of the goals scored by a player or team or any other conditins specifiedin a given situation, season type and range of seasons. 
        The lower bound and upper bound of the range are the same if a single season is requested. Otherwise pass the bounds of the range.
        if a situation is not provided, we will assume the situation to be all situations
        if a season type is not provided, we will assume the season type to be regular season"""
        goal_map_scatter_get(db, llm, conditions, season_lower_bound, season_upper_bound, situation, season_type)
        return "Goal map scatter plot generated successfully"

    @tool(args_schema=goal_map_scatter_schema)
    def shot_map_scatter(conditions, season_lower_bound =2024, season_upper_bound=2024, season_type = "regular", situation = "all"):
        """Returns a scatterplot of the shots by a  player or team or any other conditins specified in a given situation, season type and range of seasons. 
        It is the same as goal_map_scatter but for shots. It uses the same schema and arguments.
        if a situation is not provided, we will assume the situation to be all situations
        if a season type is not provided, we will assume the season type to be regular season"""
        shot_map_scatter_get(db, llm, conditions, season_lower_bound, season_upper_bound, situation, season_type)
        return "Goal map scatter plot generated successfully"

    @tool(args_schema=goal_map_scatter_schema)
    def shot_heatmap_getter(conditions, season_lower_bound =2024, season_upper_bound=2024, season_type = "regular", situation = "all"):
        """Returns a heatmap of the shots by the player or team or any other conditins specified in a given situation, season type and range of seasons. 
        Like goal_map_scatter it uses the same schema and arguments.
        if a situation is not provided, we will assume the situation to be all situations
        if a season type is not provided, we will assume the season type to be regular season
        if the user requests a heatmap of shots, or a shot heatmap, it should invoke this tool"""
        shot_heat_map_get(db, llm, conditions, season_lower_bound, season_upper_bound, situation, season_type)
        return "Shot heatmap generated successfully"

    @tool(args_schema=goal_map_scatter_schema)
    def goal_heatmap_getter(conditions, season_lower_bound =2024, season_upper_bound=2024, season_type = "regular", situation = "all"):
        """Returns a heatmap of the goals scored by the player or team or any other conditins specified, in a given situation, season type and range of seasons. 
        Like goal_map_scatter it uses the same schema and arguments.
        if a situation is not provided, we will assume the situation to be all situations
        if a season type is not provided, we will assume the season type to be regular season
        if the user requests a heatmap of goals, or a goal heatmap, it should invoke this tool"""
        goal_heat_map_get(db, llm, conditions, season_lower_bound, season_upper_bound, situation, season_type)
        return "Goal heatmap generated successfully"
    
    @tool(args_schema=goal_map_scatter_schema)
    def xg_heatmap_getter(conditions, season_lower_bound =2024, season_upper_bound=2024, season_type = "regular", situation = "all"):
        """Returns a heatmap of the average expected goals in different locations by the player or team or any other conditins specified, in a given situation, season type and range of seasons. 
        Like goal_map_scatter it uses the same schema and arguments.
        if a situation is not provided, we will assume the situation to be all situations
        if a season type is not provided, we will assume the season type to be regular season
        if the user requests a heatmap of expected goals, or an xg heatmap or a expected goal heatmap, or something similar it should invoke this tool"""
        xg_heat_map_get(db, llm, conditions, season_lower_bound, season_upper_bound, situation, season_type)
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

    chain = get_chain(db, llm)

    bio_chain = get_bio_chain(db, llm)

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
        Tool(
            name="StatisticsGetter",
            func=lambda input, **kwargs: chain.invoke({"question": input}),
            description="""Useful when you want statistics about a player, line, defensive pairing, or goalie. The tool should not be invoked with an sql query. 
                            It should be invoked with a natural language question about what statistics are needed to answer the user query.
                            It will generate and perform an sql query on data from the 2015-2024 NHL seasons. Note someone may refer to a season using two years. So the 2024-25 season
                            also counts and should be invoke this tool. Questions about current statstics should use the 2024 season. If a question about that is asked, it will return a string with the answer to that question in natural language.
                            somtimes for a ratio statistic the tool will return too names if a minumum minutes or shots against is not given. Return both, unless they are the same person. 
                            In the special case that the user asks for save percentage, despite the name, the tool will return a decimal. Keep that value as is. 
                            If the tool returns a percentage or decimal, never change it. The tool knows correct conventions.
                            If a user asks you to evaluate a player you can use this tool to get common statistics to measure performance. These include: goals, points, assists, expected goals percentage, ect.
                            If a user asks for a statistic about a line or defensive pair, for example the 'Mccabe Tanev pair' or the 'kucherov point hagel line' and this tool returns nothing, then reinvoke this tool with the names in a different order. Do this until every order has been tried.
                            The tool will only return a result in the correct order, but there is no way of knowing what that is. Try until every order fails, or you recieve a response with stat information."""
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