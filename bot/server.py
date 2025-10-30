from flask import Flask
import threading
import os

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ Bot is running!"

def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def start_server():
    threading.Thread(target=run_flask, daemon=True).start()
