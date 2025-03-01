from langchain import hub
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from chains.stats_sql_chain import get_chain
from shot_maps.shot_map_plotting import goal_map_scatter_get, shot_map_scatter_get
from chains.rag_chains import get_cba_information, get_rules_information
from chains.bio_info_chain import get_bio_chain
from schemas import goal_map_scatter_schema, rag_args_schema
# Helper function to create wrappers for tools
def create_tool_wrapper(func, vector_db):
    def wrapper(query: str):
        return func(vector_db, query)
    return wrapper

def get_agent(db, rules_db, cba_db, api_key):

    llm = ChatOpenAI(model="gpt-4o", api_key=api_key)

    @tool(args_schema=goal_map_scatter_schema)
    def goal_map_scatter(player_name, season_lower_bound =2023, season_upper_bound=2023, season_type = "regular", situation = "all"):
        """Returns a scatterplot of the goals scored by the player in a given situation, season type and range of seasons. 
        The lower bound and upper bound of the range are the same if a single season is requested. Otherwise pass the bounds of the range.
        if a situation is not provided, we will assume the situation to be all situations
        if a season type is not provided, we will assume the season type to be regular season"""
        goal_map_scatter_get(db, player_name, season_lower_bound, season_upper_bound, situation, season_type)
        return "Goal map scatter plot generated successfully"

    @tool(args_schema=goal_map_scatter_schema)
    def shot_map_scatter(player_name, season_lower_bound =2023, season_upper_bound=2023, season_type = "regular", situation = "all"):
        """Returns a scatterplot of the shots by the player in a given situation, season type and range of seasons. 
        It is the same as goal_map_scatter but for shots. It uses the same schema and arguments.
        if a situation is not provided, we will assume the situation to be all situations
        if a season type is not provided, we will assume the season type to be regular season"""
        shot_map_scatter_get(db, player_name, season_lower_bound, season_upper_bound, situation, season_type)
        return "Goal map scatter plot generated successfully"

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
        return get_rules_information(rules_db, api_key, query)

    @tool(args_schema=rag_args_schema)
    def cba_getter(query: str):
        """Returns the relevant CBA information based on the query. This tool should be invoked using the cba_db as the vector_db field which is 
        passed into the getter function. This is the collective bargaining agreement between the NHL and the NHLPA.
        This tool should be used to answer any queries about the buissness, salary cap, or salary structure in the NHL. 
        This includes hypothetical questions like 'what happens if a team goes over the cap with bonus' 'how does revenue sharing between the players work'.
        This also includes information like information about revenue, profit, or any other buissness information about the NHL. 
        If a specific component of the CBA is refrenced keep that in the response"""
        return get_cba_information(cba_db, api_key, query)


    chain = get_chain(db, api_key)

    bio_chain = get_bio_chain(db, api_key)

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
        Tool(
            name="StatisticsGetter",
            func=lambda input, **kwargs: chain.invoke({"question": input}),
            description="""Useful when you want statistics about a player, line, defensive pairing, or goalie. Any statistical question should invoke this tool.
                            It will perform an sql query on data from the 2015-2023 NHL seasons. Note someone may refer to a season using two years. So the 2023-24 season
                            also counts and should be invoke this tool. If a question about that is asked, it will return a string with the answer to that question in natural language."""
        ),
        Tool(
            name="Player_BIO_information",
            func=lambda input, **kwargs: bio_chain.invoke({"question": input}),
            description="""Useful when you want BIO information about a player, including position, handedness, height, weight, Nationality, Birthday, and team."""
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