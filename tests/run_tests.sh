#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

# Install test dependencies
echo "Installing test dependencies..."
if [ -f "$PROJECT_ROOT/test-requirements.txt" ]; then
    pip install -r "$PROJECT_ROOT/test-requirements.txt"
else
    echo "Warning: test-requirements.txt not found at $PROJECT_ROOT/test-requirements.txt"
fi

# Set up test environment variables
export OPENAI_API_KEY="sk-test-12345"
export PYTHONPATH="$PYTHONPATH:$PROJECT_ROOT"

# Use pytest's built-in monkeypatching instead of environment variables
echo "Running throttling tests..."
python -m pytest $SCRIPT_DIR/utils/test_api_throttling.py \
               $SCRIPT_DIR/utils/test_openai_throttled.py \
               $SCRIPT_DIR/utils/test_throttling_integration.py \
               $SCRIPT_DIR/utils/test_embeddings.py \
               -v --cov=$PROJECT_ROOT/src/utils/throttling --no-cov-on-fail

# If running with coverage report
if [ "$1" == "--coverage" ]; then
    echo "Generating coverage report..."
    python -m pytest --cov=$PROJECT_ROOT/src --cov-report=term-missing
fi

echo "Tests completed!" 