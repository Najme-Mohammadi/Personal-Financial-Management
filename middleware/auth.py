import jwt
from flask import request, jsonify
from functools import wraps
from models.auth import Users
from models.db import Database
from models.auth import SECRET_KEY

db = Database('file.db')
user = Users()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token is missing"}), 401

        user_data, error = verify_token(token)
        if error:
            return jsonify({"error": error}), 401

        return f(user_data, *args, **kwargs)

    return decorated
  
def verify_token(token):
    """ Verify and decode a JWT token. """
    try:
        if token.startswith("Bearer "):
            token = token.split("Bearer ")[1]

        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        
        db = Database("file.db")

        user = db.fetch_one("SELECT id, username, email FROM users WHERE id = ?", (payload["user_id"],))

        if not user:
            return None, "User not found"

        user_data = {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        }

        return user_data, None 

    except jwt.ExpiredSignatureError:
        return None, "Token expired"
      
    except jwt.InvalidTokenError:
        return None, "Invalid token" 
