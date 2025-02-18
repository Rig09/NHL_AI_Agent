from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnableBranch
from langchain_openai import ChatOpenAI
from langchain.schema.runnable import RunnableParallel, RunnableLambda
from langchain.tools import Tool
from langchain.globals import set_debug, set_verbose
#from ..shot_maps.shot_map_plotting import goal_map_scatter, shot_map_scatter
# Load environment variables from .env
set_debug(True)
set_verbose(True)

load_dotenv()

# Create a ChatOpenAI model
model = ChatOpenAI(model="gpt-4o")

def goal_map_scatter(player_name, season_type, situation, season):
    return "hello"
    #print("Generating a scatter plot of goals for")

# Define the feedback classification template
classification_template = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant in information about hockey and the NHL"),
        ("system", "that can classify the input message to tell whether someone wants statistical information about a player, a heatmap, a player card, general NHL information, or information irrelavent to hockey and the NHL"),
        ("human",
         "Classify the ask as, statistical information about a player, a scatterplot, a player card, general NHL information, or information irrelavent to hockey and the NHL {category}."),
    ]
)

stat_feedback = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant."),
        (
            "human",
            "Thank somone for asking for statistical information. provide information about {ask}",
        ),
    ]
)

scatter_feedback = Tool(
    name="GOAL MAP SCATTER",
    func=goal_map_scatter,
    description="Generates a scatter plot of a player's goals on a hockey rink, excluding empty net goals and shots from behind half",
    return_direct=True
)

card_feedback = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant."),
        (
            "human",
            "Thank somone for asking for a player card. provide information about {ask}",
        ),
    ]
)

general_feedback = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant."),
        (
            "human",
            "Thank somone for asking for general NHL information. provide information about {ask}",
        ),
    ]
)

unknown_feedback = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant."),
        (
            "human",
            "Appologize for not understanding the ask. provide information about {ask}",
        ),
    ]
)

# Define the runnable branches for handling feedback
branches = RunnableBranch(
    (
        lambda x: "statistical information about a player" in x,
        stat_feedback | model | StrOutputParser()  #
    ),
    (
        lambda x: "scatter" in x,
        scatter_feedback
    ),
    (
        lambda x: "player card" in x,
        card_feedback | model | StrOutputParser()  # 
    ),
    (
        lambda x: "general NHL information" in x,
        general_feedback | model | StrOutputParser()  #
    ),
    unknown_feedback | model | StrOutputParser()  # 
)

# Create the classification chain
classification_chain = classification_template | model | StrOutputParser()

# Combine classification and response generation into one chain
chain = classification_chain | branches

ask = "Create a scatter of shots for Sidney Crosby in the 2021 season"

result = chain.invoke({"category": ask})

print(result)