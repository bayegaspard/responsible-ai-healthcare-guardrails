import os

from flask import Flask

from routes.chat_routes import chat_bp

app = Flask(__name__)
app.register_blueprint(chat_bp)

if __name__ == "__main__":
    # Port 5050 by default, because macOS AirPlay Receiver takes port 5000.
    # Set HOST=0.0.0.0 to open the demo from other devices on the same network.
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"\n  Demo running at http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}\n")
    app.run(host=host, port=port, debug=debug)
