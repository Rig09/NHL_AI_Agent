import os
from dotenv import load_dotenv
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from typing import Optional

# SQLite configuration for Chroma
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

# Load environment variables
load_dotenv()

class EmbeddingConfig:
    def __init__(self, 
                 source_path: str, 
                 db_path: str, 
                 chunk_size: int = 1000, 
                 chunk_overlap: int = 100,
                 embedding_model: str = "text-embedding-3-small",
                 verbose: bool = False):
        self.source_path = source_path
        self.db_path = db_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        self.verbose = verbose

def log_or_print(message: str, verbose: bool = False) -> None:
    """Helper function to either print or skip based on verbose setting"""
    if verbose:
        print(message)

def create_embeddings(config: EmbeddingConfig) -> Optional[Chroma]:
    """
    Create embeddings for a given text file and store them in a Chroma database.
    
    Args:
        config (EmbeddingConfig): Configuration object containing all necessary parameters
    
    Returns:
        Optional[Chroma]: The Chroma database object if creation was necessary, None if database already existed
    """
    log_or_print(f"Processing embeddings for {config.source_path}", config.verbose)
    
    if os.path.exists(config.db_path):
        log_or_print("Vector store already exists. No need to initialize.", config.verbose)
        return None
    
    if not os.path.exists(config.source_path):
        raise FileNotFoundError(f"Source file not found at {config.source_path}")
    
    # Load and split the document
    loader = TextLoader(config.source_path, encoding='utf-8')
    documents = loader.load()
    
    text_splitter = CharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap
    )
    docs = text_splitter.split_documents(documents)
    
    log_or_print(f"Created {len(docs)} document chunks", config.verbose)
    if config.verbose:
        log_or_print(f"Sample chunk:\n{docs[0].page_content}\n", config.verbose)
    
    # Create embeddings
    log_or_print("Creating embeddings...", config.verbose)
    embeddings = OpenAIEmbeddings(model=config.embedding_model)
    
    # Create and persist the vector store
    log_or_print("Creating vector store...", config.verbose)
    db = Chroma.from_documents(
        docs,
        embeddings,
        persist_directory=config.db_path
    )
    log_or_print("Vector store creation complete", config.verbose)
    
    return db

def main():
    # Configuration for different document types
    configs = {
        "rules": EmbeddingConfig(
            source_path="../../data/rag/rules/2024-25Rules.txt",
            db_path="../../data/rag/rules/chroma_db",
            verbose=True  # Enable verbose output for testing
        ),
        "cba": EmbeddingConfig(
            source_path="../../data/rag/cba/NHLPA_NHL_MOU.txt",
            db_path="../../data/rag/cba/chroma_db",
            verbose=True  # Enable verbose output for testing
        )
    }
    
    # Process each configuration
    for doc_type, config in configs.items():
        try:
            log_or_print(f"Processing {doc_type} document", config.verbose)
            create_embeddings(config)
        except Exception as e:
            if config.verbose:
                print(f"Error processing {doc_type}: {str(e)}")

if __name__ == "__main__":
    main()