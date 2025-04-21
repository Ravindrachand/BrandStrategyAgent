import os
import feedparser
from datetime import datetime
from openai import OpenAI
from notion_client import Client
from dotenv import load_dotenv

# Load env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv(1d51f5c9589280e8a8d9e1f83aed1517)

# Clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
notion = Client(auth=NOTION_TOKEN)

# Feeds
rss_feeds = {
    "Marketing Dive": "https://www.marketingdive.com/feeds/news",
    "Branding Strategy Insider":
    "https://www.brandingstrategyinsider.com/feed",
    "Adweek": "https://www.adweek.com/feed/"
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
            "You are a CMO-level brand strategist advising leading healthcare and diagnostic brands across India and APAC.\n\n"
            "Given the following marketing article, extract insights that would be useful for:\n"
            "- Patient-centric brand building\n"
            "- Digital patient acquisition\n"
            "- Regional/Tier 2 market expansion\n"
            "- AI adoption in healthcare marketing\n\n"
            "Generate:\n"
            "### Brand Strategy Insights\n"
            "- (3 bullet points with business impact)\n\n"
            "### Recommended Brand Actions\n"
            "- (2 bullet points that are realistic and specific)\n\n"
            "### Strategic Framework\n"
            "Name: (real named framework)\n"
            "How it applies: (1–2 line explanation)\n\n"
            "Write in a concise, executive tone. Avoid generic fluff. Be sharp, business-oriented, and actionable.\n\n"
            f"Title: {title}\n\nContent: {summary}")

        response = openai_client.chat.completions.create(model="gpt-4-turbo",
                                                         messages=[{
                                                             "role":
                                                             "user",
                                                             "content":
                                                             prompt
                                                         }],
                                                         temperature=0.7)
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"❌ OpenAI GPT error (summary): {e}")
        return None


def generate_tags(title, summary):
    try:
        tag_prompt = (
            f"Based on the following article, return 3 relevant tags as a comma-separated list. Tags should reflect industry themes (e.g., AI, Retail, CMO Moves, Diagnostics, India, Healthcare, APAC).\n\n"
            f"Title: {title}\n\nSummary: {summary}")

        tag_response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{
                "role": "user",
                "content": tag_prompt
            }],
            temperature=0.5)
        tag_text = tag_response.choices[0].message.content.strip()
        tags = [t.strip() for t in tag_text.split(",") if t.strip()]
        return tags[:3]  # max 3 tags
    except Exception as e:
        print(f"❌ OpenAI GPT error (tags): {e}")
        return []


def rate_insight_quality(gpt_output):
    try:
        score_prompt = (
            f"As a senior brand strategist, rate the strategic quality of the following insight report on a scale of 1 to 10. "
            f"Explain the score in 2 lines. Here is the report:\n\n{gpt_output}"
        )
        rating = openai_client.chat.completions.create(model="gpt-4-turbo",
                                                       messages=[{
                                                           "role":
                                                           "user",
                                                           "content":
                                                           score_prompt
                                                       }],
                                                       temperature=0.3)
        return rating.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Insight scoring failed: {e}"


def push_to_notion(title, summary, insights, source, published_date, tags):
    try:
        tag_objects = [{"name": tag} for tag in tags]

        notion.pages.create(parent={"database_id": NOTION_DATABASE_ID},
                            properties={
                                "Title": {
                                    "title": [{
                                        "text": {
                                            "content": title
                                        }
                                    }]
                                },
                                "Date": {
                                    "date": {
                                        "start": published_date
                                    }
                                },
                                "Source": {
                                    "rich_text": [{
                                        "text": {
                                            "content": source
                                        }
                                    }]
                                },
                                "Summary": {
                                    "rich_text": [{
                                        "text": {
                                            "content": summary[:1900]
                                        }
                                    }]
                                },
                                "Key Insights": {
                                    "rich_text": [{
                                        "text": {
                                            "content": insights[:1900]
                                        }
                                    }]
                                },
                                "Tags": {
                                    "multi_select": tag_objects
                                }
                            })
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

                insights = generate_gpt_summary(title, summary)
                if insights:
                    print("🧠 GPT-4 Turbo response received.")
                    score = rate_insight_quality(insights)
                    print(f"📊 Insight Score: {score}")
                    published_date = clean_date(entry)
                    tags = generate_tags(title, summary)
                    print(f"🏷️ Tags: {', '.join(tags) if tags else 'None'}")
                    push_to_notion(title, summary, insights, source_name,
                                   published_date, tags)
                else:
                    print("⚠️ Skipped due to GPT failure.")
        except Exception as e:
            print(f"❌ Feed fetch failed: {e}")
    print("\n🏁 All feeds processed.")
