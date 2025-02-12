#!/bin/bash

# Ensure Conda is available
if ! command -v conda &> /dev/null; then
    echo "Conda is not installed or not available in PATH."
    exit 1
fi

# Check if Mamba is installed and use it if available
if command -v mamba &> /dev/null; then
    CONDA_CMD="mamba"
    echo "Using Mamba for faster dependency resolution."
else
    CONDA_CMD="conda"
    echo "Mamba not found. Using Conda."
fi

# Env name + yml path
ENV_NAME="NHL_AI_AGENT"
ENV_YML_PATH="env/environment.yml"

# Activate base environment
source "$(conda info --base)/etc/profile.d/conda.sh" # Ensures Conda is properly set up
conda activate base

# Check if the Conda environment already exists
if conda info --envs | grep -q "^${ENV_NAME} "; then
    echo "Conda environment '$ENV_NAME' already exists."
    echo "Updating environment from $ENV_YML_PATH..."
    
    # Update the environment if it already exists
    $CONDA_CMD env update --name $ENV_NAME --file $ENV_YML_PATH --prune
else
    echo "Conda environment '$ENV_NAME' does not exist."
    echo "Creating environment from $ENV_YML_PATH..."
    
    # Create the environment if it doesn't exist
    $CONDA_CMD env create --file $ENV_YML_PATH
fi
