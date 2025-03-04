from dotenv import load_dotenv
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
import os
import argparse
from agent.agent_main import get_agent
from utils.database_init import init_db, init_vector_db
import matplotlib.pyplot as plt

# parser = argparse.ArgumentParser()
# # Use local environment variables by default
# parser.add_argument("--remote", action="store_true", help="If specified, use remote st secrets config.Otherwise, use local dotenv.") 
# # To run local config, use streamlit run app.py
# # To run remote config, use streamlit run app.py -- --remote


# # TODO: make function cleaner, remove duplicate code, naming
def get_secrets_or_env(remote):
    if remote is True:
        MYSQL_HOST = st.secrets["MYSQL_HOST"]
        MYSQL_USER = st.secrets["MYSQL_USER"]
        MYSQL_PASSWORD = st.secrets["MYSQL_PASSWORD"]
        MYSQL_DATABASE = st.secrets["MYSQL_DATABASE"]
        open_ai_key = st.secrets["OPENAI_API_KEY"]
    else:  # Local config
        load_dotenv()
        MYSQL_HOST = os.getenv("MYSQL_HOST")
        MYSQL_USER = os.getenv("MYSQL_USER")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
        MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
        open_ai_key = os.getenv("OPENAI_API_KEY")
    return MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, open_ai_key

if "database" not in st.session_state:
    # args = parser.parse_args()
    # TODO: remote to true before pushing on this branch
    MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, open_ai_key = get_secrets_or_env(remote=True)
    
    db = init_db(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE)
    rules_db = init_vector_db('rules', open_ai_key)
    cba_db = init_vector_db('cba', open_ai_key)

if "agent_chain" not in st.session_state:
    NHLStatsAgent = get_agent(db, rules_db, cba_db, open_ai_key)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        AIMessage(content="Welcome to the NHL Stats Chatbot! Ask me anything about NHL statistics and I will do my best to answer your questions!")
    ]

st.set_page_config(page_title="NHL Stats Chatbot", page_icon="🏒", layout="wide")

st.title("NHL Stats Chatbot")

# Display the chat history
for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.markdown(message.content)

# Handle user input and update the chat history
user_query = st.chat_input("Type a message...")
if user_query is not None and user_query.strip() != "":
    # Add human message to history
    st.session_state.chat_history.append(HumanMessage(content=user_query))

    with st.chat_message("Human"):
        st.markdown(user_query)

    # Get response from the agent, passing the chat history
    with st.chat_message("AI"):
        # Pass the entire chat history to the agent
        agent_input = "\n".join([message.content for message in st.session_state.chat_history])  # Join all messages
        response = NHLStatsAgent.invoke({"input": agent_input})

        # Check that the response contains the expected 'output' key
        if isinstance(response, dict) and "output" in response:
            ai_response = response["output"]
            st.markdown(ai_response)
            
            # Append AI response to chat history
            st.session_state.chat_history.append(AIMessage(content=ai_response))

            # The agent tools will handle plot generation through their own logic
            # Any plots generated will be available in the matplotlib figure manager
            if plt.get_fignums():  # Check if any figures were created
                for fig_num in plt.get_fignums():
                    fig = plt.figure(fig_num)
                    st.pyplot(fig)
                    plt.close(fig)  # Clean up the figure
        else:
            # Handle the case where the response is not as expected
            st.markdown("Sorry, I couldn't understand that request. Please try again.")
