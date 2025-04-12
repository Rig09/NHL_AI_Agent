#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Install test dependencies
echo "Installing test dependencies..."
pip install -r ../test-requirements.txt

# Set up test environment variables
export OPENAI_API_KEY="sk-test-12345"
export PYTHONPATH="$PYTHONPATH:$(pwd)/.."
export USE_MOCK_RESPONSES="true"

# Use the test override to replace the throttling implementation
echo "Applying test patches..."
python -c "from utils.test_override import patch_throttling; patch_throttling()"

# Run the specific throttling tests
echo "Running throttling tests..."
python -m pytest utils/test_api_throttling.py \
               utils/test_openai_throttled.py \
               utils/test_throttling_integration.py \
               -v --cov=../src/utils/throttling --no-cov-on-fail

# If running with coverage report
if [ "$1" == "--coverage" ]; then
    echo "Generating coverage report..."
    python -m pytest --cov=../src --cov-report=term-missing
fi

echo "Tests completed!" 