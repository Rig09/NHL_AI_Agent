from dotenv import load_dotenv
import os
from pathlib import Path
import streamlit as st

def load_environment_config():
    """
    Load environment configuration based on deployment context.
    
    The app can run in three contexts:
    1. Local Development: Uses .env.local
       - Local MySQL database
       - Debug mode enabled
    
    2. Azure (Local Testing): Uses .env.azure
       - Azure MySQL database
       - Debug mode determined by ENVIRONMENT:
         * dev -> DEBUG=true
         * prod -> DEBUG=false
    
    3. Streamlit Cloud: Uses Streamlit secrets
       - Azure MySQL database
       - All configuration managed through Streamlit Cloud dashboard
    
    Returns:
        dict: Configuration dictionary with all necessary settings
    """
    # Check if running on Streamlit Cloud
    try:
        # Try to access secrets - this will only work on Streamlit Cloud
        _ = st.secrets["MYSQL_HOST"]
        print("Running on Streamlit Cloud - using secrets management")
        config = {
            "MYSQL_HOST": st.secrets["MYSQL_HOST"],
            "MYSQL_USER": st.secrets["MYSQL_USER"],
            "MYSQL_PASSWORD": st.secrets["MYSQL_PASSWORD"],
            "MYSQL_DATABASE": st.secrets["MYSQL_DATABASE"],
            "OPENAI_API_KEY": st.secrets["OPENAI_API_KEY"],
            "ENVIRONMENT": st.secrets.get("ENVIRONMENT", "prod"),
            "DEBUG": st.secrets.get("DEBUG", False)
        }
    except FileNotFoundError:
        # Local development - use .env files
        env = os.getenv("ENVIRONMENT", "local")
        
        # Determine which .env file to use
        if env == "local":
            env_file = Path(".env.local")
            debug_mode = True  # Local is always debug mode
        else:  # Both 'dev' and 'prod' use Azure database
            env_file = Path(".env.azure")
            debug_mode = (env == "dev")  # Debug true for dev, false for prod
        
        if env_file.exists():
            print(f"Loading configuration from: {env_file}")
            load_dotenv(dotenv_path=env_file)
        else:
            print(f"Warning: {env_file} not found, falling back to default .env")
            load_dotenv()
        
        config = {
            "MYSQL_HOST": os.getenv("MYSQL_HOST"),
            "MYSQL_USER": os.getenv("MYSQL_USER"),
            "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD"),
            "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "ENVIRONMENT": env,
            "DEBUG": debug_mode
        }
    
    # Log the current environment (but not sensitive data)
    print(f"Running in {config['ENVIRONMENT']} environment")
    print(f"Debug mode: {config['DEBUG']}")
    print(f"Using database: {config['MYSQL_DATABASE']} at {config['MYSQL_HOST']}")
    
    return config 