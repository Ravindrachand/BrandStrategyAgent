from flask import Flask, request
from agent_script import run_agent
import os

app = Flask(__name__)

@app.route("/", methods=["POST"])
def trigger_agent():
    try:
        run_agent()
        return {"status": "✅ Agent ran successfully"}, 200
    except Exception as e:
        return {"status": "❌ Error", "message": str(e)}, 500

if __name__ == "__main__":
    print("✅ Flask server is starting...")

    repl_slug = os.environ.get("REPL_SLUG", "workspace")
    repl_owner = os.environ.get("REPL_OWNER", "ravindrachand")
    public_url = f"https://{repl_slug}.{repl_owner}.repl.co"

    print(f"🌐 Your public Replit URL is: {public_url}")

    app.run(host="0.0.0.0", port=8080)
