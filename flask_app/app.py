from flask import Flask
from routes.chat_routes import chat_bp

app = Flask(__name__)

# Register blueprints
app.register_blueprint(chat_bp)

if __name__ == '__main__':
    # Port 5000 is taken by macOS AirPlay Receiver, which answers with HTTP 403.
    import os
    app.run(debug=True, port=int(os.environ.get("PORT", 5050)))
