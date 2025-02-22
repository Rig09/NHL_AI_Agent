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
from first_query_attempt import db, get_chain
from shot_maps.shot_map_plotting import goal_map_scatter_get


load_dotenv()
# Initialize a ChatOpenAI model
llm = ChatOpenAI(model="gpt-4o")

chain = get_chain()

class goal_map_scatter_schema(BaseModel):
    player_name: str = Field(title="Player Name", description="The name of the player to generate the goal map scatter plot for")
    season: int = Field(title="Season", description="""The season to generate the goal map scatter plot for. If the season is provided 
                        with 2 seasons, like 2020-2021, pass the first season as the argument. Pass this as ONLY the integer value. 
                        So if the user asks for the 2022 season. Pass the argument '2022'. DO NOT PASS 'Season 2022' Pass '2022'""")
    season_type: str = Field(title="Season Type", description="""The type of season this should be past as: 'regular', 'playoffs', or 
                             'all'. Default to passing the word 'regular' if it is not specified. The playoffs can also be called the
                              postseason, this should be passed as playoffs""")
    situation: str = Field(title="Situation", description="The situation which can be on the powerplay, even strength,"
                           "shorthanded, or all situations depending on the number of players on the ice. Default to all situations if not specified. to generate the goal map scatter plot for. Pass these situations as 5on4 for powerplay, 4on5 for shorthanded, 5on5 for even strength, and all for all situations")

@tool(args_schema=goal_map_scatter_schema)
def goal_map_scatter(player_name, season=2023, season_type = "regular", situation = "all"): #placeholder function for goal_map_scatter
    """Returns a scatterplot of the goals scored by the player in a given situation, season type and season
    if a situation is not provided, we will assume the situation to be all situations
    if a season type is not provided, we will assume the season type to be regular season"""
    goal_map_scatter_get(player_name, season, situation, season_type)
    return "Goal map scatter plot generated successfully"

memory = ConversationBufferMemory(
     memory_key="chat_history", return_messages=True)

tools = [
    goal_map_scatter,
    Tool(
    name="StatisticsGetter",
    func=lambda input, **kwargs: chain.invoke({"question": input}),
    description="""Useful when you want statistics about a player. Any statistical question should invoke this tool.
                    It will perform an sql query on data from the 2015-2023 NHL seasons. If a question about that is asked, 
                    it will return a string with the answer to that question in natural language."""
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

# response = agent_executor.invoke({"input": "How many goals did Sidney Crosby score in the 2023 regular season?"})
# print("Response:", response)

# second_response = agent_executor.invoke({"input": "Generate a goal map scatter plot for Sidney Crosby in the 2021-2022 season"})
# print("Second Response:", second_response)


while True:
    user_input = input("User: ")
    if user_input.lower() == "exit":
        memory.chat_memory.clear()
        break

    # Add the user's message to the conversation memory
    memory.chat_memory.add_message(HumanMessage(content=user_input))

    response = agent_executor.invoke({"input": user_input})
    print("Bot:", response["output"])

    # Add the agent's response to the conversation memory
    memory.chat_memory.add_message(AIMessage(content=response["output"]))
