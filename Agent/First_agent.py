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
from SQL_Chains.first_query_attempt import get_chain
from shot_maps.shot_map_plotting import goal_map_scatter_get, shot_map_scatter_get
from RAG_Chains.RAG_NHL_rules import get_rules_information
from RAG_Chains.RAG_NHL_CBA import get_cba_information
from SQL_Chains.bio_info_query import get_bio_chain
from data.database_init import init_db, init_cba_db, init_rules_db

load_dotenv()
# Initialize a ChatOpenAI model
llm = ChatOpenAI(model="gpt-4o")

class goal_map_scatter_schema(BaseModel):
    player_name: str = Field(title="Player Name", description="The name of the player to generate the goal map scatter plot for")
    season_lower_bound: int = Field(title="Season_lower_bound", description="""The first season in the range of seasons to generate the goal map scatter plot for. 
                                    Often a season can be refered to using two different years since it takes place on either side of new years,  like 'in the 2020-2021 season', 
                                    pass the first year as the argument. Another way this could be done is by only using the last two numbers of the second year. For example 2020-21 means pass '2020'
                                    Pass this as ONLY the integer value. So if the user asks for the 2022 season. Pass the argument '2022'. 
                                    DO NOT PASS 'Season 2022' Pass '2022'. When a range of seasons is provided like, 'from the 2015 to 2023 season generate a scatterplot' 
                                    This is the lower bound of the range. ie. the older year should be this value.'""")
    season_upper_bound: int = Field(title="Season_upper_bound", description="""The second season in the range of seasons to generate the goal map scatter plot for. 
                                    If only a single season is provided like 'generate a scatterplot for the 2022-23 season' then this value should be the same as season_lower_bound. 
                                    If there is a range of seasons in the request, then this should be the newest year. For example if someone asks 'generate a scatterplot for goals from the 2017-2023 seasons' 
                                    then this would take the value 2023. Someone may also say, 'generate a scatterplot from 2017-18 to 2022-23. Then the value of this would be 2022. Allways pass the fist year 
                                    if the season is given as multiple years. Interperate whether a range of seasons or single season is being requested. If it is a range, the upper bound should be this value.
                                    If it is a single, this value should be the same as lower_bound_season. 
                                    DO NOT PASS 'Season 2022' Pass '2022'""")
    season_type: str = Field(title="Season Type", description="""The type of season this should be past as: 'regular', 'playoffs', or 
                             'all'. Default to passing the word 'regular' if it is not specified. The playoffs can also be called the
                              postseason, this should be passed as playoffs""")
    situation: str = Field(title="Situation", description="The situation which can be on the powerplay, even strength," 
                           "shorthanded, or all situations depending on the number of players on the ice. Default to all situations if not specified. to generate the goal map scatter plot for. Pass these situations as 5on4 for powerplay, 4on5 for shorthanded, 5on5 for even strength, and all for all situations")

class rag_args_schema(BaseModel):
    #vector_db: Any = Field(..., description='A vector database for the RAG chain to interact with. This should be passed to the tool from the rules_db or cba_db depending on the tool used')
    query: str = Field(..., description='The query to be executed by a RAG system. This will be fed into a function which will provide an answer to the query based on text files relevant to the query')

def get_agent(db):


    chain = get_chain(db)

    bio_chain = get_bio_chain(db)

    memory = ConversationBufferMemory(
        memory_key="chat_history", return_messages=True)

    # # Wrap the rule_getter and cba_getter functions to keep signature intact
    # rule_getter_wrapped = create_tool_wrapper(rule_getter, rules_db)
    # cba_getter_wrapped = create_tool_wrapper(cba_getter, cba_db)

    tools = [
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
            description="""Useful when you want BIO information about a player, including position, handedness, height, weight, Nationality, Birthday, and team."""
        )
    ]
    
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