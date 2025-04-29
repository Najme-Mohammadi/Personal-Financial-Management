from models.db import Database

db = Database('file.db')


db.execute("""
CREATE TABLE IF NOT EXISTS users(
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       username TEXT UNIQUE NOT NULL CHECK(length(username)>= 3 AND length(username) <= 20),
       email TEXT UNIQUE NOT NULL CHECK(length(email) <= 50),
       password TEXT NOT NULL, 
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP          
 )
""")

db.execute("""
CREATE TABLE IF NOT EXISTS categories(
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           name TEXT NOT NULL CHECK(length(name) > 0),
           type TEXT CHECK(type IN('income', 'expense')) NOT NULL,
           user_id INTEGER,
           FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
           UNIQUE(name, user_id)
)
""")

db.execute("""
INSERT INTO categories (name, type) VALUES 
    ('Salary', 'income'),  
    ('Gift', 'income'),
    ('Food', 'expense'),
    ('Rent', 'expense'),
    ('Transport', 'expense'),
    ('Entertainment', 'expense'),
    ('Shopping', 'expense')
ON CONFLICT(name, user_id) DO NOTHING;
""")

db.execute("""
CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            amount REAL NOT NULL,  -- Positive for income, negative for expenses
            description TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE          
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS groups(
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           name TEXT NOT NULL,
           created_by INTEGER NOT NULL,
           total_amount REAL DEFAULT 0,
           member_count INTEGER DEFAULT 1,
           FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
           UNIQUE(name, created_by)  -- This line ensures no duplicate group name per user
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS group_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    amount_spent REAL DEFAULT 0,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (group_id, user_id) 
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS group_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    user_id INTEGER, -- optional for spent
    amount_spent REAL, -- optional for spent
    from_user INTEGER, -- for debt calculations
    to_user INTEGER,   -- for debt calculations
    amount REAL,       -- for debt calculations
    description TEXT,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (from_user) REFERENCES users(id),
    FOREIGN KEY (to_user) REFERENCES users(id)
)
""")