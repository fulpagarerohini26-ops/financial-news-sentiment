# financial-news-sentiment-git-repo
financial-news-sentiment capstone project

# GenAI-Powered Financial News Sentiment Analyzer
1. Problem Statement
In today’s fast-paced financial markets, investors and analysts face challenges in keeping up with real-time financial news and understanding its potential impact on stock performance. Traditional methods of sentiment tracking are often limited in scope and speed.
 This project aims to leverage Large Language Models (LLMs) and Natural Language Processing (NLP) techniques to extract, analyze, and visualize market sentiment from real-time financial news. The goal is to assist financial analysts and traders in making data-driven investment decisions by correlating news sentiment with stock market trends.

2. Objective
●	To build an AI-powered financial sentiment analyzer that:

○	Fetches real-time financial news using APIs such as Finnhub.

○	Performs sentiment analysis (positive, negative, neutral) on headlines and summaries.

○	Visualizes sentiment trends and evaluates their impact on stock price movements.

3. About the Data
●	Source: Finnhub.io Financial API

●	Type of Data: Real-time and historical financial news, stock price data, and sentiment indicators.

4. Technical Approach
●	Step 1: Use the Finnhub API to fetch company-specific news articles.

●	Step 2: Perform text preprocessing and sentiment analysis using TextBlob or VADER.

●	Step 3: Compute overall sentiment polarity scores for both headlines and summaries.

●	Step 4: Visualize the sentiment trend and analyze its correlation with stock price movement.

●	Step 5: Extend the system with LLM-based contextual sentiment understanding (e.g., GPT or fine-tuned LLaMA model).


5. Example Code
import finnhub
import pandas as pd
from textblob import TextBlob
import matplotlib.pyplot as plt

# Initialize API client
finnhub_client = finnhub.Client(api_key='ADD_YOUR_API_KEY_HERE')

# Fetch company news (Example: Apple)
res = finnhub_client.company_news('AAPL', _from="2025-01-01", to="2025-01-31")
news_df = pd.DataFrame(res)

# Perform sentiment analysis
news_df['headline_sentiment'] = news_df['headline'].apply(lambda x: TextBlob(x).sentiment.polarity)
news_df['summary_sentiment'] = news_df['summary'].apply(lambda x: TextBlob(x).sentiment.polarity)

# Compute average sentiment
avg_sentiment = news_df[['headline_sentiment', 'summary_sentiment']].mean()

print("Average Headline Sentiment:", avg_sentiment['headline_sentiment'])
print("Average Summary Sentiment:", avg_sentiment['summary_sentiment'])


6. NLP Use Cases
1.	Sentiment Analysis – Identify and quantify the emotional tone (positive, negative, neutral) of financial news articles.

2.	Impact Analysis – Evaluate how sentiment fluctuations correlate with stock price changes or market volatility.

3.	Market Prediction Support – Use historical sentiment patterns to provide predictive insights for trading strategies.
