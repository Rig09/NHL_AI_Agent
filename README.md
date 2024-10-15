# Expected by Whom?: NHL Expected Goals Modelling
In this repository, we explore a variety of approaches to model expected goals (xG), which quantify the value of a hockey scoring chance. For more information on xG modelling and its history, see this article from [Evolving Hockey](https://evolving-hockey.com/blog/a-new-expected-goals-model-for-predicting-goals-in-the-nhl/).

<!-- TODO: Should there be more of an explanation into xG? -->

### Data Source
NHL play by play data was collected using the [hockey-scraper](https://github.com/HarryShomer/Hockey-Scraper/tree/master) Python package. Our modelling uses data from _TODO: START SEASON_ until the end of the 2022-23 NHL season.

- How did we get the raw data? Link to section in the code?

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

### Authors
Adrian Rigby, [GitHub](https://github.com/RIGBY/), [LinkedIn](https://linkedin.com/RIGBY/)
<!-- TODO: Add Adrian's GitHub -->
Leo Sandler: [GitHub](https://github.com/L-Sandler/), [LinkedIn](https://www.linkedin.com/in/leo-sandler/)