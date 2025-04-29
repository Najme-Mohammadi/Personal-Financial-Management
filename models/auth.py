import bcrypt
import jwt
import datetime
from models.db import Database
import re
import html

#in env file?
SECRET_KEY = "secret_key"

class Users:
    def __init__(self):
        self.db = Database('file.db')

    @staticmethod
    def hash_password(password):
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed

    @staticmethod
    def validate_inputs(username, email, password):

        username = html.escape(username).strip()  # Removes <script> tags and other HTML elements
        email = email.lower().strip()  # Normalize email case

        # Validate username
        if not username or len(username) < 3 or len(username) > 20:
         raise ValueError("Username must be between 3 and 20 characters.")
        
        # Validate email
        if not email or len(email) > 50 or not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
            raise ValueError("Invalid e-mail address.")
        
        # Validate password
        if not password or not re.match(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$", password):
            raise ValueError("Password must be at least 6 characters long, include a number and a letter.")
        return True

    def create_user(self, username, email, password):
        self.validate_inputs(username, email, password)

        if self.find_by_email_or_username(email) or self.find_by_email_or_username(username):
            raise ValueError("Username or e-mail already exists.")
        
        hashed_password = self.hash_password(password)
        query = "INSERT INTO users (username, email, password) VALUES (?, ?, ?)"
        
        try:
            self.db.execute(query, (username, email, hashed_password))
            return {"message": "User created successfully."}
        except Exception as e:
            return {"error": str(e)}
        
    def verify_user(self, identifier, password):
        query = "SELECT password FROM users WHERE username = ? OR email = ?"
        user = self.db.fetch_one(query, (identifier, identifier))
        
        if user:
            stored_password_hash = user['password']
            return bcrypt.checkpw(password.encode('utf-8'), stored_password_hash)
        return False

    def login_user(self, identifier, password):
        user = self.find_by_email_or_username(identifier)

        if not user:
            raise ValueError("User not found.")
            
        if not self.verify_user(identifier, password):
            raise ValueError("Invalid username/email or password.")
       
        return {"message": "Login successful", "user_id": user['id']}

    def find_by_email_or_username(self, identifier):
       try:
         query = "SELECT * FROM users WHERE username = ? OR email = ?"
         user = self.db.fetch_one(query, (identifier, identifier))
         return user
       
       except Exception as e:
        return None
    

    def find_all(self):
        query = "SELECT id, username, email FROM users"
        return self.db.fetch_all(query)
    
    def find_username_by_id(self, user_id):
        query = "SELECT username FROM users WHERE id = ?"
        result = self.db.fetch_one(query, (user_id,))
        if result:
            return result["username"]
        return None
 
    @staticmethod
    def generate_token(user_id, is_refresh=False):
        exp_time = datetime.timedelta(days=7) if is_refresh else datetime.timedelta(minutes=15) 
        payload = {
            "user_id": user_id,
            "exp": datetime.datetime.utcnow() + exp_time ,# Expires in 1 hour
            "type": "refresh" if is_refresh else "access"
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return token
    @staticmethod
    def verify_token(token, expected_type="access"):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            
            if payload.get("type") != expected_type:
                return{"valid": False, "error": f"Invalid token type. Expected {expected_type}"}
            return {"valid": True, "user_id": payload["user_id"]}
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError:
            return {"valid": False, "error": "Invalid token"}