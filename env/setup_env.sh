#!/bin/bash

# Name of the environment
ENV_NAME="nhl_ai_agent"

# Path to the environment.yml file inside the env folder
ENV_YML_PATH="env/environment.yml"

# TODO: Deactivate any currently active conda environment???

# Check if the conda environment already exists
if conda info --envs | grep -q "^${ENV_NAME} "; then
    echo "Conda environment '$ENV_NAME' already exists."
    echo "Updating environment from $ENV_YML_PATH..."
    
    # Update the environment if it already exists
    conda env update --name $ENV_NAME --file $ENV_YML_PATH --prune
else
    echo "Conda environment '$ENV_NAME' does not exist."
    echo "Creating environment from $ENV_YML_PATH..."
    
    # Create the environment if it doesn't exist
    conda env create --file $ENV_YML_PATH
fi

# Activate the environment
echo "Activating environment..."
conda activate $ENV_NAME
