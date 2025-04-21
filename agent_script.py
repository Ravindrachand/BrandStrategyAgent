import os
import feedparser
from datetime import datetime
from openai import OpenAI
from notion_client import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
notion = Client(auth=NOTION_TOKEN)

# Expanded Feeds (15 Top-Tier Sources)
rss_feeds = {
    "Marketing Dive": "https://www.marketingdive.com/feeds/news",
    "Branding Strategy Insider": "https://www.brandingstrategyinsider.com/feed",
    "Adweek": "https://www.adweek.com/feed/",
    "Healthcare IT News": "https://www.healthcareitnews.com/rss",
    "MedCity News": "https://medcitynews.com/feed/",
    "Fierce Healthcare": "https://www.fiercehealthcare.com/rss.xml",
    "Modern Healthcare": "https://www.modernhealthcare.com/feeds",
    "Harvard Business Review Strategy": "https://hbr.org/section/strategy/rss",
    "Marketing Week": "https://www.marketingweek.com/feed/",
    "Contagious": "https://www.contagious.com/feed",
    "McKinsey Healthcare": "https://www.mckinsey.com/industries/healthcare/our-insights/rss",
    "Deloitte Healthcare": "https://www2.deloitte.com/us/en/insights/rss.xml",
    "WARC Strategy": "https://www.warc.com/Topics/Strategy.topicRSS",
    "TechCrunch Health": "https://techcrunch.com/category/health/feed/",
    "World Economic Forum Healthcare": "https://www.weforum.org/agenda/archive/health/feed"
}

def clean_date(entry):
    try:
        if hasattr(entry, "published_parsed"):
            return datetime(*entry.published_parsed[:6]).isoformat()
    except:
        pass
    return datetime.utcnow().isoformat()

def generate_gpt_summary(title, summary):
    try:
        prompt = (
            "You are a Senior Partner at a global consulting firm, advising Fortune 500 healthcare and diagnostic companies.\n\n"
            "Analyze the following article for strategic intelligence relevant to:\n"
            "- Patient-centric brand positioning\n"
            "- Digital patient acquisition\n"
            "- Regional expansion opportunities\n"
            "- Emerging technologies in diagnostics and preventive care\n"
            "- Market threats and opportunities\n\n"
            "**Your Output:**\n\n"
            "### Strategic Insights\n"
            "• (3 sharply-worded, high-impact insights)\n\n"
            "### Recommended Actions\n"
            "• (2 realistic, specific, and strategic actions)\n\n"
            "### Emerging Threat/Opportunity\n"
            "• (Identify 1 major threat or opportunity emerging)\n\n"
            "### Strategic Framework\n"
            "- Name a real-world framework (e.g., Ansoff Matrix, Porter's Five Forces)\n"
            "- 1–2 lines explaining relevance\n\n"
            "Stay sharply analytical, CXO-level tone, no fluff.\n\n"
            f"Title: {title}\n\nArticle Content: {summary}"
        )

        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"\u274c OpenAI GPT error (summary): {e}")
        return None

def generate_tags(title, summary):
    try:
        tag_prompt = (
            f"Based on the following article, return 3 relevant tags as a comma-separated list. Tags should reflect industry themes (e.g., AI, Retail, CMO Moves, Diagnostics, India, Healthcare, APAC).\n\n"
            f"Title: {title}\n\nSummary: {summary}"
        )

        tag_response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": tag_prompt}],
            temperature=0.5
        )
        tag_text = tag_response.choices[0].message.content.strip()
        tags = [t.strip() for t in tag_text.split(",") if t.strip()]
        return tags[:3]
    except Exception as e:
        print(f"\u274c OpenAI GPT error (tags): {e}")
        return []

def rate_insight_quality(gpt_output):
    try:
        score_prompt = (
            f"As a senior brand strategist, rate the strategic quality of the following insight report on a scale of 1 to 10. "
            f"Explain the score in 2 lines.\n\nHere is the report:\n\n{gpt_output}"
        )
        rating = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": score_prompt}],
            temperature=0.3
        )
        return rating.choices[0].message.content.strip()
    except Exception as e:
        return f"\u26a0\ufe0f Insight scoring failed: {e}"

def push_to_notion(title, summary, insights, source, published_date, tags):
    try:
        tag_objects = [{"name": tag} for tag in tags]

        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Title": {"title": [{"text": {"content": title}}]},
                "Date": {"date": {"start": published_date}},
                "Source": {"rich_text": [{"text": {"content": source}}]},
                "Summary": {"rich_text": [{"text": {"content": summary[:1900]}}]},
                "Key Insights": {"rich_text": [{"text": {"content": insights[:1900]}}]},
                "Tags": {"multi_select": tag_objects}
            }
        )
        print(f"\u2705 Notion page created for: {title}")
    except Exception as e:
        print(f"\u274c Failed to create Notion page for '{title}': {e}")

def run_agent():
    for source_name, url in rss_feeds.items():
        print(f"\n\ud83d\udce1 Fetching feed: {source_name}")
        try:
            feed = feedparser.parse(url)
            print(f"\ud83d\udcc1 Found {len(feed.entries)} articles.")
            for entry in feed.entries[:5]:
                title = entry.get("title", "Untitled")
                summary = entry.get("summary", entry.get("description", ""))
                print(f"\n\ud83d\udcdd Processing article: {title}")

                insights = generate_gpt_summary(title, summary)
                if insights:
                    print("\ud83e\udde0 GPT-4 Turbo response received.")
                    score = rate_insight_quality(insights)
                    print(f"\ud83d\udcca Insight Score: {score}")
                    published_date = clean_date(entry)
                    tags = generate_tags(title, summary)
                    print(f"\ud83c\udff7\ufe0f Tags: {', '.join(tags) if tags else 'None'}")
                    push_to_notion(title, summary, insights, source_name, published_date, tags)
                else:
                    print("\u26a0\ufe0f Skipped due to GPT failure.")
        except Exception as e:
            print(f"\u274c Feed fetch failed: {e}")
    print("\n\ud83c\udfc1 All feeds processed.")
