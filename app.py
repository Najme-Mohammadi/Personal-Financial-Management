from flask import Flask, g
from flasgger import Swagger
from flask import jsonify
from routes.routes import auth_bp
from routes.routes import dashboard_bp
from routes.routes import dutch_bp
from models.db import Database
from extensions import limiter
from flask_limiter.errors import RateLimitExceeded

app = Flask(__name__) 
swagger = Swagger(app)

limiter.init_app(app)

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(dutch_bp)


@app.errorhandler(RateLimitExceeded)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded. Please wait."}), 429

# @app.route('/', methods=['GET']) 
# def home():
#     return "Welcome"

db = Database("file.db")
    
if __name__ == '__main__':
    app.run(debug = True, port=5001)