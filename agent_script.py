import os
import feedparser
import re
from datetime import datetime
from openai import OpenAI
from notion_client import Client
from dotenv import load_dotenv

# Load env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
notion = Client(auth=NOTION_TOKEN)

# Expanded RSS Feeds
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

def generate_gpt_outputs(title, summary):
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
            "- (3 sharply-worded, high-impact insights)\n\n"
            "### Recommended Actions\n"
            "- (2 realistic, specific, and strategic actions)\n\n"
            "### Strategic Framework\n"
            "- Name a real-world framework (e.g., Ansoff Matrix, Porter's Five Forces) and explain how it applies.\n\n"
            "Be sharply analytical, executive in tone, no generic fluff. Write for CXO-level consumption.\n\n"
            f"Title: {title}\n\nArticle Content: {summary}"
        )

        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )

        full_content = response.choices[0].message.content.strip()

        # Splitting outputs
        strategic_insights = ""
        recommended_actions = ""
        strategic_framework = ""

        if "### Strategic Insights" in full_content:
            strategic_insights = full_content.split("### Strategic Insights")[1].split("### Recommended Actions")[0].strip()

        if "### Recommended Actions" in full_content:
            recommended_actions = full_content.split("### Recommended Actions")[1].split("### Strategic Framework")[0].strip()

        if "### Strategic Framework" in full_content:
            strategic_framework = full_content.split("### Strategic Framework")[1].strip()

        return strategic_insights, recommended_actions, strategic_framework

    except Exception as e:
        print(f"❌ GPT error (outputs): {e}")
        return None, None, None

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
        print(f"❌ GPT error (tags): {e}")
        return []

def rate_insight_quality(insights):
    try:
        score_prompt = (
            f"Rate the strategic quality of the following insights strictly on a scale of 1 to 10. Only reply with the number, no explanation.\n\nInsights:\n{insights}"
        )
        rating_response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": score_prompt}],
            temperature=0.0
        )
        rating_text = rating_response.choices[0].message.content.strip()

        # Extract just the number
        score_match = re.search(r'\d+', rating_text)
        if score_match:
            return int(score_match.group(0))
        else:
            return None
    except Exception as e:
        return None

def push_to_notion(title, summary, insights, actions, framework, score, source, published_date, tags):
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
                "Recommended Actions": {"rich_text": [{"text": {"content": actions[:1900]}}]},
                "Strategic Framework": {"rich_text": [{"text": {"content": framework[:1900]}}]},
                "Insight Score": {"number": score},
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

                insights, actions, framework = generate_gpt_outputs(title, summary)

                if insights and actions and framework:
                    print("🧠 GPT-4 Turbo outputs received.")
                    score = rate_insight_quality(insights)
                    print(f"📊 Insight Score: {score}")
                    published_date = clean_date(entry)
                    tags = generate_tags(title, summary)
                    print(f"🏷️ Tags: {', '.join(tags) if tags else 'None'}")

                    push_to_notion(title, summary, insights, actions, framework, score, source_name, published_date, tags)
                else:
                    print("⚠️ Skipped due to GPT failure.")

        except Exception as e:
            print(f"❌ Feed fetch failed: {e}")
    print("\n🏁 All feeds processed.")
