import sqlite3
from config import Config
from datetime import datetime, timedelta
import os
from werkzeug.security import generate_password_hash

def drop_tables(cur):
    tables = ['transactions', 'budgets', 'savings_goals', 'bank_connections', 'users']
    for table in tables:
        cur.execute(f"DROP TABLE IF EXISTS {table}")

def create_tables(cur):
    # Create users table first
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login DATETIME
    )""")

    # Create transactions table with user_id foreign key
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date DATETIME NOT NULL,
        description TEXT NOT NULL,
        amount DECIMAL(10,2) NOT NULL,
        category TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
        payment_method TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    # Create budgets table with user_id
    cur.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        amount DECIMAL(10,2) NOT NULL,
        period TEXT NOT NULL DEFAULT 'monthly',
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        alert_threshold DECIMAL(5,2) DEFAULT 80.0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    # Create savings_goals table with user_id
    cur.execute("""
    CREATE TABLE IF NOT EXISTS savings_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        target_amount DECIMAL(10,2) NOT NULL,
        current_amount DECIMAL(10,2) DEFAULT 0,
        deadline DATE,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

def insert_sample_data(cur):
    # Create admin user
    from werkzeug.security import generate_password_hash
    admin_password_hash = generate_password_hash('admin123')
    cur.execute("""
        INSERT INTO users (username, email, password_hash, is_admin)
        VALUES (?, ?, ?, 1)
    """, ('admin', 'admin@example.com', admin_password_hash))
    admin_id = cur.lastrowid

    # Create some sample regular users
    sample_users = [
        ('user1', 'user1@example.com', generate_password_hash('user123')),
        ('user2', 'user2@example.com', generate_password_hash('user123')),
        ('user3', 'user3@example.com', generate_password_hash('user123'))
    ]
    
    for username, email, password_hash in sample_users:
        cur.execute("""
            INSERT INTO users (username, email, password_hash, is_admin)
            VALUES (?, ?, ?, 0)
        """, (username, email, password_hash))
    
    # Insert sample budgets with user_id
    today = datetime.now()
    month_end = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    sample_budgets = [
        (admin_id, 'Food', 500.00, today.date(), month_end.date()),
        (admin_id, 'Transportation', 200.00, today.date(), month_end.date()),
        (admin_id, 'Entertainment', 150.00, today.date(), month_end.date()),
        (admin_id, 'Utilities', 300.00, today.date(), month_end.date()),
    ]
    
    cur.executemany("""
    INSERT INTO budgets (user_id, category, amount, start_date, end_date)
    VALUES (?, ?, ?, ?, ?)
    """, sample_budgets)

def init_db():
    # Ensure the database directory exists
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Drop existing tables for clean initialization
    drop_tables(cur)
    
    # Create tables
    create_tables(cur)
    
    # Check if admin user exists
    cur.execute("SELECT * FROM users WHERE is_admin = 1")
    admin = cur.fetchone()
    
    if not admin:
        # Create default admin user
        admin_password = 'admin123'  # Default password
        admin_password_hash = generate_password_hash(admin_password)
        
        cur.execute("""
            INSERT INTO users (username, email, password_hash, is_admin)
            VALUES (?, ?, ?, 1)
        """, ('admin', 'admin@example.com', admin_password_hash))
        
        print("Default admin user created:")
        print("Username: admin")
        print("Password: admin123")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()
