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
from imported_chain import get_chain

load_dotenv()
# Initialize a ChatOpenAI model
llm = ChatOpenAI(model="gpt-4o")

chain = get_chain()

class goal_map_scatter_schema(BaseModel):
    player_name: str = Field(title="Player Name", description="The name of the player to generate the goal map scatter plot for")
    season: str = Field(title="Season", description="The season to generate the goal map scatter plot for")
    season_type: str = Field(title="Season Type", description="The type of season, regular season or playoffs (also known as postseason). Default to regular season if not provided. to generate the goal map scatter plot for")
    situation: str = Field(title="Situation", description="The situation which can be on the powerplay, even strength, shorthanded, or all situations depending on the number of players on the ice. Default to all situations if not specified. to generate the goal map scatter plot for")

@tool(args_schema=goal_map_scatter_schema)
def goal_map_scatter(player_name, season, season_type = "regular", situation = "all"): #placeholder function for goal_map_scatter
    """Returns a scatterplot of the goals scored by the player in a given situation, season type and season"""
    return f"Generating a scatter plot of {situation} goals for {player_name} in {season_type} season {season}"



tools = [
    goal_map_scatter,
    Tool(
    name="JokeTeller",
    func=lambda input, **kwargs: chain.invoke({"input": input}),
    description="Useful when you want to tell a joke",
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
)

#response = chain.invoke({"input": "Tell me a joke."})
response = agent_executor.invoke({"input": "Tell me a joke."})
print("Response:", response)

second_response = agent_executor.invoke({"input": "Generate a goal map scatter plot for Sidney Crosby in the 2021-2022 season"})
print("Second Response:", second_response)
