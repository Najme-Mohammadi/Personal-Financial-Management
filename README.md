# 💼 Flask SQLite Backend API

This is a lightweight and secure Flask backend API built with SQLite. It includes user authentication, category management, token-based access, and proper database connection handling using Flask's application context (`g`) and teardown mechanisms.

---

## 🚀 Features

- ✅ User registration and login with hashed passwords
- 🔐 JWT-based authentication
- 🗂 Category management (personal and global)
- 🧠 Token decoding and validation
- 💾 SQLite database with a custom DB class
- 🧹 Automatic DB connection closing using `teardown_appcontext`

---

## 🧱 Tech Stack

- **Python 3**
- **Flask**
- **SQLite**
- **bcrypt**
- **JWT (PyJWT)**

---

## 📁 Project Structure

project/ │ ├── app.py # Main Flask app and routes ├── database.py # SQLite DB class ├── auth.py # Authentication and token handling ├── routes/ │ └── category.py # Category-related endpoints ├── models/ # Optional: DB models ├── utils/ # Optional: helper functions ├── file.db # SQLite database file └── README.md # This file

yaml
Copy
Edit

---

## 🛠 Setup & Installation

1. **Clone the repo**

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
Create a virtual environment

bash
Copy
Edit
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install dependencies

bash
Copy
Edit
pip install -r requirements.txt
Run the app

bash
Copy
Edit
python app.py
🔐 Authentication Flow
Users register with username/email/password.

On login, a JWT token is generated and returned.

Token is required in headers (Authorization: Bearer <token>) for protected endpoints.

📦 Example Endpoints
POST /register – create new user

POST /login – user login

GET /categories – list categories

POST /categories – create a category (token required)

🔁 Teardown Explained
Every request will automatically close the SQLite connection using:

python
Copy
Edit
@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()
This avoids open connections and potential memory leaks.

✅ TODOs
 Add pagination support

 Add category editing

 Write unit tests

 Add Swagger or Postman documentation

📄 License
MIT License. Free to use and modify!

🙋‍♀️ Contributions
Contributions, issues, and feature requests are welcome!
Feel free to fork and submit a PR.

vbnet
Copy
Edit

Let me know if you want to include more technical details or Postman collection links!
