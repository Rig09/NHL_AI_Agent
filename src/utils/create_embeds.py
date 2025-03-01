import os
from dotenv import load_dotenv
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

load_dotenv()

current_dir = os.path.dirname(os.path.realpath(__file__))
file_path = os.path.join(current_dir,'PDFS', '2024-25Rules.txt')
persistent_dir = os.path.join(current_dir, 'PDFS', 'rules_chroma_db')

print('NHL Rulebook embeddings')
if not os.path.exists(persistent_dir):

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at {file_path}")
    
    loader = TextLoader(file_path, encoding='utf-8')
    documents = loader.load()


    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)
    # Display information about the split documents
    print("\n--- Document Chunks Information ---")
    print(f"Number of document chunks: {len(docs)}")
    print(f"Sample chunk:\n{docs[0].page_content}\n")

    # Create embeddings
    print("\n--- Creating embeddings ---")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )  # Update to a valid embedding model if needed
    print("\n--- Finished creating embeddings ---")

    # Create the vector store and persist it automatically
    print("\n--- Creating vector store ---")
    db = Chroma.from_documents(
        docs, embeddings, persist_directory=persistent_dir)
    print("\n--- Finished creating vector store ---")

else:
    print("Vector store already exists. No need to initialize.")

file_path = os.path.join(current_dir,'PDFS', 'NHLPA_NHL_MOU.txt')
persistent_dir = os.path.join(current_dir, 'PDFS', 'cba_chroma_db')

print('Creating embeddings for CBA')

if not os.path.exists(persistent_dir):

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at {file_path}")
    
    loader = TextLoader(file_path, encoding='utf-8')
    documents = loader.load()

    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)
    # Display information about the split documents
    print("\n--- Document Chunks Information ---")
    print(f"Number of document chunks: {len(docs)}")
    print(f"Sample chunk:\n{docs[0].page_content}\n")

    # Create embeddings
    print("\n--- Creating embeddings ---")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )  # Update to a valid embedding model if needed
    print("\n--- Finished creating embeddings ---")

    # Create the vector store and persist it automatically
    print("\n--- Creating vector store ---")
    db = Chroma.from_documents(
        docs, embeddings, persist_directory=persistent_dir)
    print("\n--- Finished creating vector store ---")

else:
    print("Vector store already exists. No need to initialize.")