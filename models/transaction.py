from datetime import datetime

class Transaction:
    CATEGORIES = [
        'Salary', 'Investment', 'Food', 'Transportation', 'Housing',
        'Utilities', 'Healthcare', 'Entertainment', 'Shopping', 'Education',
        'Savings', 'Other'
    ]
    
    PAYMENT_METHODS = [
        'Cash', 'Credit Card', 'Debit Card', 'Bank Transfer', 
        'E-Wallet', 'Direct Deposit'
    ]
    
    def __init__(self, id=None, user_id=None, date=None, description=None, 
                 amount=None, category=None, type=None, payment_method=None, 
                 notes=None):
        self.id = id
        self.user_id = user_id
        self.date = date or datetime.now()
        self.description = description
        self.amount = amount
        self.category = category
        self.type = type  # 'income' or 'expense'
        self.payment_method = payment_method
        self.notes = notes

    @staticmethod
    def from_db_row(row):
        return Transaction(
            id=row['id'],
            user_id=row['user_id'],
            date=datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S'),
            description=row['description'],
            amount=float(row['amount']),
            category=row['category'],
            type=row['type'],
            payment_method=row['payment_method'],
            notes=row['notes']
        )
