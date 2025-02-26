from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_openai import ChatOpenAI


load_dotenv()
# Initialize a ChatOpenAI model
model = ChatOpenAI(model="gpt-4o")

# Define prompt templates (no need for separate Runnable chains)
prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a comedian who tells jokes about hockey."),
        ("human", "{input}"),
    ]
)

# Create the combined chain using LangChain Expression Language (LCEL)
# chain = prompt_template | model | StrOutputParser()
chain = prompt_template | model| StrOutputParser()

def get_chain():
    return chain