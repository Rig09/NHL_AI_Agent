from dotenv import load_dotenv
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
import os
from agent.agent_main import get_agent
from utils.database_init import init_db, init_vector_db
import matplotlib.pyplot as plt
from langchain_openai import ChatOpenAI

def get_secrets_or_env(remote):
    if remote:
        MYSQL_HOST = st.secrets["MYSQL_HOST"]
        MYSQL_USER = st.secrets["MYSQL_USER"]
        MYSQL_PASSWORD = st.secrets["MYSQL_PASSWORD"]
        MYSQL_DATABASE = st.secrets["MYSQL_DATABASE"]
        open_ai_key = st.secrets["OPENAI_API_KEY"]
    else:
        load_dotenv()
        MYSQL_HOST = os.getenv("MYSQL_HOST")
        MYSQL_USER = os.getenv("MYSQL_USER")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
        MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
        open_ai_key = os.getenv("OPENAI_API_KEY")
    return MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, open_ai_key

if "database" not in st.session_state:
    MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, open_ai_key = get_secrets_or_env(remote=True)
    
    db = init_db(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE)
    rules_db = init_vector_db('rules', open_ai_key)
    cba_db = init_vector_db('cba', open_ai_key)

if "agent_chain" not in st.session_state:
    NHLStatsAgent = get_agent(db, rules_db, cba_db, open_ai_key, llm=ChatOpenAI(model="gpt-4o", api_key=open_ai_key))

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        AIMessage(content="Welcome to the NHL Stats Chatbot! Ask me anything about NHL statistics and I will do my best to answer your questions!")
    ]

st.set_page_config(page_title="NHL Stats Chatbot", page_icon="🏒", layout="wide")
st.title("NHL Chatbot")
st.write("Credit [moneypuck.com](https://moneypuck.com/) for all the player, shot, line, and goalie data used in this project.")

# Track sample query usage
if "selected_query_used" not in st.session_state:
    st.session_state.selected_query_used = False

def on_select_change():
    st.session_state.selected_query_used = True

sample_queries = [
    "What is Snowflake?",
    "What company did Snowflake announce they would acquire in October 2023?",
    "What company did Snowflake acquire in March 2022?",
    "When did Snowflake IPO?"
]

selected_query = st.selectbox(
    "Here are some sample queries that you can try:",
    sample_queries,
    index=0,
    on_change=on_select_change
)

# Display the chat history
for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.markdown(message.content)

# Handle user input
user_query = st.chat_input("Type a message...")

if not user_query and st.session_state.selected_query_used:
    user_query = selected_query

if user_query:
    st.session_state.chat_history.append(HumanMessage(content=user_query))
    with st.chat_message("Human"):
        st.markdown(user_query)

    try:
        with st.chat_message("AI"):
            agent_input = "\n".join([message.content for message in st.session_state.chat_history])
            response = NHLStatsAgent.invoke({"input": agent_input})

            if isinstance(response, dict) and "output" in response:
                ai_response = response["output"]
                st.markdown(ai_response)
                st.session_state.chat_history.append(AIMessage(content=ai_response))

                if plt.get_fignums():
                    for fig_num in plt.get_fignums():
                        fig = plt.figure(fig_num)
                        st.pyplot(fig)
                        plt.close(fig)
            else:
                st.markdown("Sorry, I couldn't understand that request. Please try again.")

    except Exception as e:
        if str(e) == "There was an error with the query. Please try again with a different query.":
            st.error("There was an issue with your query. Please modify your query and try again.")
        else:
            st.error("An unexpected error occurred. Please try again later.")
            st.write(f"Error details: {e}")
