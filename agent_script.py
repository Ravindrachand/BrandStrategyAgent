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

# Feeds (Expanded list)
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

def generate_gpt_analysis(title, summary):
    try:
        prompt = (
            "You are a Senior Partner at a global consulting firm, advising Fortune 500 healthcare and diagnostic companies.\n\n"
            "Analyze the following article for strategic intelligence relevant to:\n"
            "- Patient-centric brand positioning\n"
            "- Digital patient acquisition\n"
            "- Regional expansion opportunities\n"
            "- Emerging technologies in diagnostics and preventive care\n\n"
            "**Your Output:**\n"
            "### Strategic Insights\n"
            "• (3 sharply-worded, high-impact insights)\n\n"
            "### Recommended Actions\n"
            "• (2 realistic, specific, strategic actions)\n\n"
            "### Strategic Framework\n"
            "- Name a real-world strategic framework (e.g., Ansoff Matrix, Porter's Five Forces)\n"
            "- 1–2 lines on how it applies\n\n"
            "Stay sharply analytical, business-savvy, and executive-focused. Avoid generic fluff.\n\n"
            f"Title: {title}\n\nArticle Content: {summary}"
        )

        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"❌ OpenAI GPT error (analysis): {e}")
        return None

def generate_tags(title, summary):
    try:
        tag_prompt = (
            f"Based on the following article, return 3 relevant tags as a comma-separated list focused on marketing, branding, healthcare, diagnostics, digital trends.\n\n"
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
        print(f"❌ OpenAI GPT error (tags): {e}")
        return []

def rate_insight_quality(gpt_output):
    try:
        score_prompt = (
            f"Rate the strategic quality of the following insights on a scale of 1–10.\n\n{gpt_output}"
        )

        rating = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": score_prompt}],
            temperature=0.3
        )
        return rating.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ Insight scoring failed: {e}")
        return None

def extract_sections(gpt_response):
    try:
        sections = {"Insights": "", "Actions": "", "Framework": ""}
        if "### Strategic Insights" in gpt_response:
            parts = gpt_response.split("### ")
            for part in parts:
                if part.startswith("Strategic Insights"):
                    sections["Insights"] = part.split("\n",1)[1].strip()
                elif part.startswith("Recommended Actions"):
                    sections["Actions"] = part.split("\n",1)[1].strip()
                elif part.startswith("Strategic Framework"):
                    sections["Framework"] = part.split("\n",1)[1].strip()
        return sections
    except Exception as e:
        print(f"⚠️ Section parsing failed: {e}")
        return {"Insights": "", "Actions": "", "Framework": ""}

def push_to_notion(title, summary, insights, actions, framework, source, published_date, tags, score):
    try:
        tag_objects = [{"name": tag} for tag in tags]

        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Title": {"title": [{"text": {"content": title}}]},
                "Date": {"date": {"start": published_date}},
                "Source": {"rich_text": [{"text": {"content": source}}]},
                "Summary": {"rich_text": [{"text": {"content": insights[:1900]}}]},
                "Recommend Action": {"rich_text": [{"text": {"content": actions[:1900]}}]},
                "Strategic Framework": {"rich_text": [{"text": {"content": framework[:1900]}}]},
                "Insight Score": {"number": float(score) if score else 0},
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

                gpt_response = generate_gpt_analysis(title, summary)
                if gpt_response:
                    print("🧠 GPT-4 Turbo analysis received.")
                    sections = extract_sections(gpt_response)
                    score = rate_insight_quality(gpt_response)
                    published_date = clean_date(entry)
                    tags = generate_tags(title, summary)

                    push_to_notion(title, summary, sections["Insights"], sections["Actions"], sections["Framework"],
                                   source_name, published_date, tags, score)
                else:
                    print("⚠️ Skipped due to GPT failure.")
        except Exception as e:
            print(f"❌ Feed fetch failed: {e}")
    print("\n🏁 All feeds processed.")
