from dotenv import load_dotenv
from langchain import hub
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import Tool, StructuredTool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain.schema.output_parser import StrOutputParser
#from imported_chain import get_chain
from first_query_attempt import get_chain
from shot_maps.shot_map_plotting import goal_map_scatter_get, shot_map_scatter_get
from RAG_NHL_rules import get_rules_information
from RAG_NHL_CBA import get_cba_information
from bio_info_query import get_bio_chain


load_dotenv()
# Initialize a ChatOpenAI model
llm = ChatOpenAI(model="gpt-4o")

class goal_map_scatter_schema(BaseModel):
    player_name: str = Field(title="Player Name", description="The name of the player to generate the goal map scatter plot for")
    season: int = Field(title="Season", description="""The season to generate the goal map scatter plot for. If the season is provided 
                            with 2 seasons, like 2020-2021, pass the first season as the argument. Another way this could be done is
                             by only using the last two numbers of the second year. For example 2020-21 means pass '2020'
                             Pass this as ONLY the integer value. So if the user asks for the 2022 season. Pass the argument '2022'. 
                            DO NOT PASS 'Season 2022' Pass '2022'""")
    season_type: str = Field(title="Season Type", description="""The type of season this should be past as: 'regular', 'playoffs', or 
                             'all'. Default to passing the word 'regular' if it is not specified. The playoffs can also be called the
                              postseason, this should be passed as playoffs""")
    situation: str = Field(title="Situation", description="The situation which can be on the powerplay, even strength,"
                           "shorthanded, or all situations depending on the number of players on the ice. Default to all situations if not specified. to generate the goal map scatter plot for. Pass these situations as 5on4 for powerplay, 4on5 for shorthanded, 5on5 for even strength, and all for all situations")

@tool(args_schema=goal_map_scatter_schema)
def goal_map_scatter(player_name, season=2023, season_type = "regular", situation = "all"):
    """Returns a scatterplot of the goals scored by the player in a given situation, season type and season
    if a situation is not provided, we will assume the situation to be all situations
    if a season type is not provided, we will assume the season type to be regular season"""
    goal_map_scatter_get(player_name, season, situation, season_type)
    return "Goal map scatter plot generated successfully"

@tool(args_schema=goal_map_scatter_schema)
def shot_map_scatter(player_name, season=2023, season_type = "regular", situation = "all"):
    """Returns a scatterplot of the shots by the player in a given situation, season type and season. It is the same as goal_map_scatter but for shots. It uses the same schema and arguments.
    if a situation is not provided, we will assume the situation to be all situations
    if a season type is not provided, we will assume the season type to be regular season"""
    shot_map_scatter_get(player_name, season, situation, season_type)
    return "Goal map scatter plot generated successfully"

class rag_args_schema(BaseModel):
    query: str = Field('''The query to be excucuted by a rag system. This will be fed into a function which will provide an answer to the query based on text files relavent to the query''')

@tool(args_schema=rag_args_schema)
def rule_getter(query: str):
    """Returns the relevant rule information based on the query. Any query about a hypothetical situation in hockey should use this tool
    For example: 'what happens if...', preceeded by an event that could occur in a game.
    Use this tool when the user asks about an NHL rule. For example 'can you kick a puck into 
    the net' or 'what is offside'. This function will also return the rule numbers referenced. 
    Please keep those in the response.
    When THIS TOOL IS CALLED KEEP THE SPECIFIC RULE NUMBER IN THE RESPONSE 
    for example at the end of a response it could say (RULE 48.2) keep that rule refrence"""
    return get_rules_information(query)

@tool(args_schema=rag_args_schema)
def cba_getter(query: str):
    """Returns the relevant CBA information based on the query. This is the collective bargaining agreement between the NHL and the NHLPA.
    This tool should be used to answer any queries about the buissness, salary cap, or salary structure in the NHL. This includes hypothetical questions like,
    'what happens if a team goes over the cap with bonus' 'how does revenue sharing between the players work'. This also includes information like information about revenue, profit, or any other buissness information about the NHL. 
    If a specific component of the CBA is refrenced keep that in the response"""
    return get_cba_information(query)


def get_agent(db):
    chain = get_chain(db)

    bio_chain = get_bio_chain(db)

    memory = ConversationBufferMemory(
        memory_key="chat_history", return_messages=True)

    tools = [
        goal_map_scatter,
        shot_map_scatter,
        rule_getter,
        cba_getter,
        Tool(
        name="StatisticsGetter",
        func=lambda input, **kwargs: chain.invoke({"question": input}),
        description="""Useful when you want statistics about a player, line, defensive pairing, or goalie. Any statistical question should invoke this tool.
                        It will perform an sql query on data from the 2015-2023 NHL seasons. If a question about that is asked, 
                        it will return a string with the answer to that question in natural language."""
        ),
        Tool(
        name="Player_BIO_information",
        func=lambda input, **kwargs: bio_chain.invoke({"question": input}),
        description="""Useful when you want BIO information about a player, including position, handedness, height, weight, Nationality, Birthday, and team. """
        )
    ]
    # Pull the prompt template from the hub
    prompt = hub.pull("hwchase17/openai-tools-agent")

    # Create the ReAct agent using the create_tool_calling_agent function
    # This function sets up an agent capable of calling tools based on the provided prompt.
    agent = create_tool_calling_agent(
        llm=llm,  # Language model to use
        tools=tools,  # List of tools available to the agent
        prompt=prompt,  # Prompt template to guide the agent's responses 
    )

    # Create the agent executor
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,  # The agent to execute
        tools=tools,  # List of tools available to the agent
        #verbose=True,  # Enable verbose logging
        handle_parsing_errors=True,  # Handle parsing errors gracefully
        memory=memory,
    )
    return agent_executor
# response = agent_executor.invoke({"input": "How many goals did Sidney Crosby score in the 2023 regular season?"})
# print("Response:", response)

# second_response = agent_executor.invoke({"input": "Generate a goal map scatter plot for Sidney Crosby in the 2021-2022 season"})
# print("Second Response:", second_response)

#third_response = agent_executor.invoke({"input": "What is icing in hockey?"})
#print("Third Response:", third_response)

# while True:
#     user_input = input("User: ")
#     if user_input.lower() == "exit":
#         memory.chat_memory.clear()
#         break

#     # Add the user's message to the conversation memory
#     memory.chat_memory.add_message(HumanMessage(content=user_input))

#     response = agent_executor.invoke({"input": user_input})
#     print("Bot:", response["output"])

#     # Add the agent's response to the conversation memory
#     memory.chat_memory.add_message(AIMessage(content=response["output"]))
