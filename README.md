# NHL AI Agent
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_red.svg)](https://nhlchatbot.streamlit.app/)

AI Agent created using [LangChain](https://www.langchain.com). 
Currently a demo using Streamlit is up and running and can be found at: https://nhlchatbot.streamlit.app/

### Citations
- Thank you [MoneyPuck](https://moneypuck.com) for providing all data used for statistical queries
- CBA and NHL rulebook sourced from the [official NHL website](https://www.nhl.com/)
- [The Commute Sports](https://thecommutesports.com/2022/08/06/creating-nhl-shot-maps-with-python/) for a starting point and inspiration on plotting hockey data.

### Authors
Adrian Rigby, [GitHub](https://github.com/Rig09/), [LinkedIn](https://www.linkedin.com/in/adrian-rigby-9293bb272/)
Leo Sandler: [GitHub](https://github.com/L-Sandler/), [LinkedIn](https://www.linkedin.com/in/leo-sandler/)

More detailed README file to come.

## Running Tests

This project uses pytest for testing. Test dependencies are kept separate from main application dependencies in the `test-requirements.txt` file.

### Local Testing

To run tests locally:

```bash
# Install test dependencies and run tests
./run_tests.sh

# Run tests with coverage report
./run_tests.sh --coverage
```

### Docker Testing

To run tests in Docker:

```bash
# Build the test container
docker build -f Dockerfile.test -t nhl-ai-agent-test .

# Run tests in the container
docker run nhl-ai-agent-test
```
