# NHL AI Agent
<!-- TODO: Explain XG Context -->
<!-- TODO: Explain AI Agent Context -->

## Repository Setup
### Data Fetching
To clone all of the necessary input data from this project, run the `data_install.sh` shell script (from the root directory).

_Bash Terminal Code
```
chmod +x data_install.sh
./data_install.sh
```

### Conda Environment
To create a Conda environment with all required packages, run the following bash commands (starting from the root directory):
- Line 1 gives exec permission to the shell script
- Lines 2 and 3 allow conda commands to be run in a bash terminal and reset the bash profile
- Line 4 runs the script and line 5 activates the NHL_AI_AGENT Conda environment

_Bash Terminal Code_
```
chmod +x ./env/setup_env.sh
conda init bash
source ~/.bashrc
./env/setup_env.sh
conda activate NHL_AI_AGENT
```

### Data Preprocessing and Feature Extraction
- Missing values, categorical features, which features we created.
- Link to sections in the code

### Model Selection
Leading xG models use Logistic Regression or Gradient Boosted models ([source](https://evolving-hockey.com/blog/a-new-expected-goals-model-for-predicting-goals-in-the-nhl/)). We implmented these approaches with our data, to assess performance relative to existing models (this also verifies that our feature extraction is done correctly, by comparing results to the current state of the art).
- Link to section in the code

### Model Training and Hyperparameter Tuning

### Model Testing and Evaluation

### Visualization?

### Future Work?

### Citations
- Link in all python packages
- Cite [MoneyPuck](https://moneypuck.com) data

### Authors
Adrian Rigby, [GitHub](https://github.com/Rig09/), [LinkedIn](https://www.linkedin.com/in/adrian-rigby-9293bb272/)
Leo Sandler: [GitHub](https://github.com/L-Sandler/), [LinkedIn](https://www.linkedin.com/in/leo-sandler/)