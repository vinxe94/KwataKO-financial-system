from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, username=None, email=None, password=None, id=None, is_admin=False):
        self.id = id
        self.username = username
        self.email = email
        self.is_admin = is_admin
        if password:
            self.set_password(password)
        else:
            self.password_hash = None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def from_db_row(row):
        if not row:
            return None
        user = User()
        user.id = row['id']
        user.username = row['username']
        user.email = row['email']
        user.password_hash = row['password_hash']
        user.is_admin = bool(row.get('is_admin', 0))
        return user

    def deactivate(self):
        self.active = False

    def activate(self):
        self.active = True
        
    @property
    def status(self):
        return 'Active' if getattr(self, 'active', True) else 'Inactive'

    @staticmethod
    def create_user(db_connection, username, email, password, is_admin=False):
        try:
            # First check if username or email already exists
            cur = db_connection.cursor()
            cur.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
            if cur.fetchone():
                raise ValueError("Username or email already exists")

            # Create new user
            user = User(username=username, email=email, password=password, is_admin=is_admin)
            
            # Insert into database
            cur.execute("""
                INSERT INTO users (username, email, password_hash, is_admin, active)
                VALUES (?, ?, ?, ?, ?)
            """, (user.username, user.email, user.password_hash, user.is_admin, True))
            
            db_connection.commit()
            return user
        except Exception as e:
            db_connection.rollback()
            raise Exception(f"Failed to create user: {str(e)}")

    @staticmethod
    def get_all_users(db_connection):
        cur = db_connection.cursor()
        cur.execute("""
            SELECT u.*, 
                   COALESCE(SUM(CASE 
                       WHEN t.type = 'income' THEN t.amount 
                       WHEN t.type = 'expense' THEN -t.amount 
                       ELSE 0 
                   END), 0) as balance
            FROM users u
            LEFT JOIN transactions t ON u.id = t.user_id
            GROUP BY u.id
        """)
        return [User.from_db_row(dict(row)) for row in cur.fetchall()]

    @staticmethod
    def toggle_user_status(db_connection, user_id):
        cur = db_connection.cursor()
        cur.execute("UPDATE users SET active = NOT active WHERE id = ?", (user_id,))
        db_connection.commit()

    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False
