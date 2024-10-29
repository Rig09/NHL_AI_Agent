#!/bin/bash

# Ensure Conda is available
if ! command -v conda &> /dev/null; then
    echo "Conda is not installed or not available in PATH."
    exit 1
fi

# Env name + yml path
ENV_NAME="NHL_AI_AGENT"
ENV_YML_PATH="env/environment.yml"

# Activates base environment
source "$(conda info --base)/etc/profile.d/conda.sh" # This ensures conda is set up
conda activate base

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