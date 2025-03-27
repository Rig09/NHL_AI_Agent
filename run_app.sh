#!/bin/bash

# Script to run the Streamlit app in different environments

# Define valid environments
VALID_ENVS=("local" "dev" "prod")

# Function to print usage
print_usage() {
    echo "Usage: ./run_app.sh [local|dev|prod]"
    echo
    echo "Environments:"
    echo "  local - Local development with local MySQL database (Debug: ON)"
    echo "  dev   - Azure database with development settings (Debug: ON)"
    echo "  prod  - Azure database with production settings (Debug: OFF)"
    echo
}

# Check if help is requested
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    print_usage
    exit 0
fi

# Check if environment argument is provided
if [ -z "$1" ]; then
    echo "No environment specified, defaulting to local"
    ENV="local"
else
    ENV=$1
    # Validate environment
    if [[ ! " ${VALID_ENVS[@]} " =~ " ${ENV} " ]]; then
        echo "Error: Invalid environment '$ENV'"
        echo
        print_usage
        exit 1
    fi
fi

# Check if required .env file exists
ENV_FILE=".env.${ENV}"
if [ "$ENV" != "local" ]; then
    ENV_FILE=".env.azure"
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Environment file '$ENV_FILE' not found"
    echo "Please create the appropriate .env file before running the app"
    exit 1
fi

# Set the environment
export ENVIRONMENT=$ENV

# Print the environment configuration
echo "Starting app with configuration:"
echo "--------------------------------"
echo "Environment: $ENV"
echo "Config file: $ENV_FILE"
echo "Debug mode : $([ "$ENV" == "prod" ] && echo "OFF" || echo "ON")"
echo "Database   : $([ "$ENV" == "local" ] && echo "Local MySQL" || echo "Azure MySQL")"
echo "--------------------------------"

# Run the Streamlit app
streamlit run src/app.py 