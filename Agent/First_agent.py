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
from SQL_Chains.bio_info_query import get_bio_chain
from data.database_init import init_db, init_cba_db, init_rules_db

def get_agent(db, api_key):

    llm = ChatOpenAI(model="gpt-4o", api_key=api_key)
    chain = get_chain(db, api_key)

    bio_chain = get_bio_chain(db, api_key)

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
                            It will perform an sql query on data from the 2015-2023 NHL seasons. Note someone may refer to a season using two years. So the 2023-24 season
                            also counts and should be invoke this tool. If a question about that is asked, it will return a string with the answer to that question in natural language."""
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