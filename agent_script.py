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

# Initialize clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
notion = Client(auth=NOTION_TOKEN)

# Expanded Feeds
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
    "Contagious": "https://www.contagious.com/feed"
}

def clean_date(entry):
    try:
        if hasattr(entry, "published_parsed"):
            return datetime(*entry.published_parsed[:6]).isoformat()
    except:
        pass
    return datetime.utcnow().isoformat()

def generate_gpt_output(title, summary):
    try:
        prompt = (
            "You are a Senior Partner at a global consulting firm, advising Fortune 500 healthcare and diagnostic companies.\n\n"
            "Analyze the following article for strategic intelligence relevant to:\n"
            "- Patient-centric brand positioning\n"
            "- Digital patient acquisition\n"
            "- Regional expansion opportunities\n"
            "- Emerging technologies in diagnostics and preventive care\n\n"
            "**Your Output:**\n\n"
            "### Strategic Insights\n"
            "• (3 sharply-worded, high-impact insights)\n\n"
            "### Recommended Actions\n"
            "• (2 realistic, specific, strategic actions)\n\n"
            "### Strategic Framework\n"
            "- Name a real-world framework (e.g., Ansoff Matrix, Porter's Five Forces) and how it applies in 2 lines\n\n"
            "### Insight Quality Rating\n"
            "- Rate the overall strategic insightfulness of the article on a scale of 1 to 10 and justify it in 2 lines.\n\n"
            "Be executive, sharp, and specific. Avoid fluff.\n\n"
            f"Title: {title}\n\nArticle Content: {summary}"
        )

        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"❌ OpenAI GPT error: {e}")
        return None

def parse_gpt_output(gpt_output):
    sections = {
        "insights": "",
        "actions": "",
        "framework": "",
        "score": ""
    }
    try:
        if "### Strategic Insights" in gpt_output:
            insights_part = gpt_output.split("### Strategic Insights")[1]
            if "### Recommended Actions" in insights_part:
                sections["insights"], insights_part = insights_part.split("### Recommended Actions", 1)
                if "### Strategic Framework" in insights_part:
                    sections["actions"], insights_part = insights_part.split("### Strategic Framework", 1)
                    if "### Insight Quality Rating" in insights_part:
                        sections["framework"], sections["score"] = insights_part.split("### Insight Quality Rating", 1)
    except Exception as e:
        print(f"⚠️ Parsing error: {e}")

    return {k: v.strip() for k, v in sections.items()}

def generate_tags(title, summary):
    try:
        tag_prompt = (
            f"Based on the following article, suggest 3 relevant industry-related tags (comma separated).\n\n"
            f"Title: {title}\n\nSummary: {summary}"
        )
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": tag_prompt}],
            temperature=0.4
        )
        tag_text = response.choices[0].message.content.strip()
        return [tag.strip() for tag in tag_text.split(",") if tag.strip()][:3]
    except Exception as e:
        print(f"❌ OpenAI GPT error (tags): {e}")
        return []

def push_to_notion(title, summary, parsed, source, published_date, tags):
    try:
        tag_objects = [{"name": tag} for tag in tags]

        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Title": {"title": [{"text": {"content": title}}]},
                "Date": {"date": {"start": published_date}},
                "Source": {"rich_text": [{"text": {"content": source}}]},
                "Summary": {"rich_text": [{"text": {"content": summary[:1900]}}]},
                "Key Insights": {"rich_text": [{"text": {"content": parsed["insights"][:1900]}}]},
                "Recommended Actions": {"rich_text": [{"text": {"content": parsed["actions"][:1900]}}]},
                "Strategic Framework": {"rich_text": [{"text": {"content": parsed["framework"][:1900]}}]},
                "Insight Score": {"rich_text": [{"text": {"content": parsed["score"][:1900]}}]},
                "Tags": {"multi_select": tag_objects}
            }
        )
        print(f"✅ Notion page created for: {title}")
    except Exception as e:
        print(f"❌ Failed to create Notion page for '{title}': {e}")

def run_agent():
    for source_name, url in rss_feeds.items():
        print(f"\n📡 Fetching feed: {source_name}")
        try:
            feed = feedparser.parse(url)
            print(f"📑 Found {len(feed.entries)} articles.")
            for entry in feed.entries[:5]:
                title = entry.get("title", "Untitled")
                summary = entry.get("summary", entry.get("description", ""))
                print(f"\n📝 Processing article: {title}")

                gpt_output = generate_gpt_output(title, summary)
                if gpt_output:
                    parsed = parse_gpt_output(gpt_output)
                    published_date = clean_date(entry)
                    tags = generate_tags(title, summary)
                    push_to_notion(title, summary, parsed, source_name, published_date, tags)
                else:
                    print("⚠️ Skipped due to GPT failure.")
        except Exception as e:
            print(f"❌ Feed fetch failed: {e}")

    print("\n🏁 All feeds processed.")
