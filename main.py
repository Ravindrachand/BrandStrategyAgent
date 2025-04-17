
import os
import openai
import requests
from datetime import datetime
from notion_client import Client
import feedparser

# Load environment variables (for local testing or Replit Secrets)
openai.api_key = os.getenv("OPENAI_API_KEY")
notion_token = os.getenv("NOTION_TOKEN")
notion_db_id = os.getenv("NOTION_DATABASE_ID")

notion = Client(auth=notion_token)

# Example RSS feeds
RSS_FEEDS = [
    "https://www.marketingdive.com/rss/",
    "https://www.brandingstrategyinsider.com/feed",
    "https://adage.com/section/news/feed",
]

# Function to fetch and parse RSS items
def fetch_articles():
    articles = []
    for feed_url in RSS_FEEDS:
        parsed_feed = feedparser.parse(feed_url)
        for entry in parsed_feed.entries[:2]:  # Limit to 2 per source for testing
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.get("summary", "")[:500]  # Limit size
            })
    return articles

# Function to generate strategic insight using GPT
def analyze_article(article_text, title):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a senior marketing strategist. Summarize the article, extract 3 strategic insights, 2 brand actions, and 1 strategic framework."},
            {"role": "user", "content": f"Article Title: {title}"}


Content:
{article_text}"}
        ]
    )
    return response.choices[0].message.content.strip()

# Function to send insights to Notion
def send_to_notion(insight_text, title, source):
    today = datetime.today().strftime('%Y-%m-%d')
    notion.pages.create(
        parent={"database_id": notion_db_id},
        properties={
            "Title": {"title": [{"text": {"content": title}}]},
            "Date": {"date": {"start": today}},
            "Source": {"rich_text": [{"text": {"content": source}}]},
            "Summary": {"rich_text": [{"text": {"content": insight_text[:200]}}]},
            "Key Insights": {"rich_text": [{"text": {"content": insight_text}}]},
            "Recommended Actions": {"rich_text": [{"text": {"content": "See insights"}}]},
            "Strategic Framework": {"rich_text": [{"text": {"content": "See insights"}}]}
        }
    )

def main():
    articles = fetch_articles()
    for article in articles:
        try:
            print(f"Processing: {article['title']}")
            gpt_output = analyze_article(article['summary'], article['title'])
            send_to_notion(gpt_output, article['title'], article['link'])
        except Exception as e:
            print(f"Failed to process article: {article['title']} → {e}")

if __name__ == "__main__":
    main()
