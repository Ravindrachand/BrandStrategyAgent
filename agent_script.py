import os
import feedparser
from datetime import datetime
from openai import OpenAI
from notion_client import Client
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Clients
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
    "HBR Strategy": "https://hbr.org/section/strategy/rss",
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

def generate_gpt_summary(title, summary):
    try:
        prompt = (
            "You are a Senior Partner at a global consulting firm, advising Fortune 500 healthcare and diagnostic companies.\n\n"
            "Analyze the following article for strategic intelligence relevant to:\n"
            "- Patient-centric brand positioning\n"
            "- Digital patient acquisition\n"
            "- Regional expansion opportunities\n"
            "- Emerging technologies in diagnostics and preventive care\n\n"
            "**Your Output (strictly follow this structure):**\n\n"
            "### Strategic Insights\n"
            "(3 sharply-worded bullet points)\n\n"
            "### Recommended Actions\n"
            "(2 realistic, strategic action points)\n\n"
            "### Strategic Framework\n"
            "(Mention 1 real-world framework and 1–2 lines why it applies)\n\n"
            "### Insight Score\n"
            "(Score between 1 and 10)\n\n"
            "### Insight Score Rationale\n"
            "(2 lines explaining why you gave that score)\n\n"
            "Keep the tone executive, concise, and sharp.\n\n"
            f"Title: {title}\n\nArticle Content: {summary}"
        )

        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"❌ OpenAI GPT error (summary): {e}")
        return None

def extract_sections(gpt_text):
    try:
        insights = recommended_actions = framework = score = rationale = ""

        # Extract sections cleanly
        insights_match = re.search(r"### Strategic Insights\s*(.*?)###", gpt_text, re.DOTALL)
        recommended_match = re.search(r"### Recommended Actions\s*(.*?)###", gpt_text, re.DOTALL)
        framework_match = re.search(r"### Strategic Framework\s*(.*?)###", gpt_text, re.DOTALL)
        score_match = re.search(r"### Insight Score\s*(.*?)###", gpt_text, re.DOTALL)
        rationale_match = re.search(r"### Insight Score Rationale\s*(.*)", gpt_text, re.DOTALL)

        if insights_match:
            insights = insights_match.group(1).strip()

        if recommended_match:
            recommended_actions = recommended_match.group(1).strip()

        if framework_match:
            framework = framework_match.group(1).strip()

        if score_match:
            try:
                score = int(re.findall(r"\d+", score_match.group(1))[0])
            except:
                score = 1  # default if not parsed

        if rationale_match:
            rationale = rationale_match.group(1).strip()

        return insights, recommended_actions, framework, score, rationale

    except Exception as e:
        print(f"❌ Section parsing error: {e}")
        return "", "", "", 1, ""

def generate_tags(title, summary):
    try:
        tag_prompt = (
            f"Based on the following article, return 3 relevant tags as a comma-separated list. Tags should reflect strategic business themes (e.g., AI, Diagnostics, Tier 2 Expansion, Preventive Health, Healthcare Marketing).\n\n"
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

def push_to_notion(title, summary, insights, recommended_actions, framework, score, rationale, source, published_date, tags):
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
                "Recommended Actions": {"rich_text": [{"text": {"content": recommended_actions[:1900]}}]},
                "Strategic Framework": {"rich_text": [{"text": {"content": framework[:1900]}}]},
                "Insight Score": {"number": score},
                "Insight Score Rationale": {"rich_text": [{"text": {"content": rationale[:1900]}}]},
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

                gpt_output = generate_gpt_summary(title, summary)
                if gpt_output:
                    insights, recommended_actions, framework, score, rationale = extract_sections(gpt_output)
                    published_date = clean_date(entry)
                    tags = generate_tags(title, summary)

                    push_to_notion(
                        title, summary, insights, recommended_actions, framework,
                        score, rationale, source_name, published_date, tags
                    )

                else:
                    print("⚠️ Skipped due to GPT failure.")
        except Exception as e:
            print(f"❌ Feed fetch failed: {e}")

    print("\n🏁 All feeds processed successfully!")
