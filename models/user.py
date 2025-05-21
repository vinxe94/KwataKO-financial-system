from werkzeug.security import generate_password_hash, check_password_hash

class User:
    def __init__(self, username=None, email=None, password=None, id=None):
        self.id = id
        self.username = username
        self.email = email
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
        return user
