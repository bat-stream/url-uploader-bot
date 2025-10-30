from bot.main import app
from bot.server import start_server

if __name__ == "__main__":
    start_server()
    print("🚀 Starting bot...")
    app.run()
