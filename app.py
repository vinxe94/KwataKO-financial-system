from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from models.transaction import Transaction
from models.user import User
from config import Config
from datetime import datetime, timedelta
from collections import defaultdict
import os
import logging
from logging.handlers import RotatingFileHandler
from init_db import init_db
from functools import wraps
from models.insights import InsightsGenerator

# Setup logging
def setup_logging(app):
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler(app.config['LOG_FILE'], maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Financial application startup')

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            app.logger.warning(f'Unauthorized access attempt to {request.endpoint}')
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.config['DEBUG'] = False  # Disable debug mode by default

class TransactionRepository:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_all(self, user_id):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM transactions 
                WHERE user_id = ? 
                ORDER BY date DESC""", (user_id,))
            return [Transaction.from_db_row(dict(row)) for row in cur.fetchall()]

    def add(self, transaction):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO transactions (user_id, date, description, amount, 
                                       category, type, payment_method, notes) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (transaction.user_id, transaction.date, transaction.description, 
                  transaction.amount, transaction.category, transaction.type,
                  transaction.payment_method, transaction.notes))
            conn.commit()

    def get_by_id(self, id):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM transactions WHERE id = ?", (id,))
            row = cur.fetchone()
            return Transaction.from_db_row(dict(row)) if row else None

    def update(self, transaction):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE transactions 
                SET date=?, description=?, amount=?, category=?, type=?, payment_method=?, notes=?
                WHERE id=?
            """, (transaction.date, transaction.description, transaction.amount,
                  transaction.category, transaction.type, transaction.payment_method, transaction.notes, 
                  transaction.id))
            conn.commit()

    def delete(self, id):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM transactions WHERE id = ?", (id,))
            conn.commit()

    def get_summary(self, start_date=None, end_date=None):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT category, SUM(amount) as total
                FROM transactions 
                WHERE date BETWEEN ? AND ?
                GROUP BY category
            """, (start_date, end_date))
            return cur.fetchall()

    def get_by_date_range(self, start_date, end_date):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM transactions 
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC
            """, (start_date, end_date))
            return [Transaction.from_db_row(dict(row)) for row in cur.fetchall()]

    def get_recent_transactions(self, user_id, limit=10):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM transactions 
                WHERE user_id = ?
                ORDER BY date DESC LIMIT ?
            """, (user_id, limit))
            return [Transaction.from_db_row(dict(row)) for row in cur.fetchall()]

    def get_budget_status(self, user_id):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT b.id, b.category, 
                       b.amount as budget_amount,
                       b.period,
                       b.alert_threshold,
                       b.start_date,
                       b.end_date,
                       COALESCE(SUM(t.amount), 0) as spent_amount,
                       (COALESCE(SUM(t.amount), 0) / b.amount * 100) as progress
                FROM budgets b
                LEFT JOIN transactions t ON b.category = t.category
                AND t.date BETWEEN b.start_date AND b.end_date
                AND t.type = 'expense'
                WHERE b.user_id = ?
                GROUP BY b.id, b.category, b.amount, b.period, b.alert_threshold, b.start_date, b.end_date
            """, (user_id,))
            return [{
                'id': row['id'],
                'category': row['category'],
                'amount': float(row['budget_amount']),
                'period': row['period'],
                'alert_threshold': float(row['alert_threshold']),
                'start_date': row['start_date'],
                'end_date': row['end_date'],
                'spent': float(row['spent_amount']),
                'progress': min(100, float(row['progress']))
            } for row in cur.fetchall()]

    def get_total_balance(self, user_id):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT COALESCE(
                    SUM(CASE WHEN type = 'income' THEN amount 
                        WHEN type = 'expense' THEN -amount END), 
                    0) as balance
                FROM transactions
                WHERE user_id = ?
            """, (user_id,))
            return float(cur.fetchone()[0])

    def get_monthly_summary(self, user_id):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT strftime('%Y-%m', date) as month,
                       SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
                       SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expenses
                FROM transactions
                WHERE user_id = ?
                GROUP BY strftime('%Y-%m', date)
                ORDER BY month DESC LIMIT 12
            """, (user_id,))
            return [dict(row) for row in cur.fetchall()]

    def get_savings_goals(self):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM savings_goals WHERE status = 'active'")
            return [dict(row) for row in cur.fetchall()]

    def get_user_by_username(self, username):
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cur.fetchone()
                return User.from_db_row(dict(row)) if row else None
        except sqlite3.OperationalError as e:
            print(f"Database error: {e}")
            init_db()  # Reinitialize database if tables are missing
            return None

    def add_user(self, user):
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO users (username, email, password_hash) 
                    VALUES (?, ?, ?)
                """, (user.username, user.email, user.password_hash))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            flash('Username or email already exists')
            return False
        except Exception as e:
            print(f"Error adding user: {e}")
            flash('An error occurred while registering')
            return False

    def update_user_settings(self, user_id, settings):
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                for key, value in settings.items():
                    cur.execute(f"""
                        UPDATE users 
                        SET {key} = ?
                        WHERE id = ?
                    """, (value, user_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating user settings: {e}")
            return False

    def get_category_summary(self, user_id):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT category, SUM(amount) as total
                FROM transactions
                WHERE user_id = ? AND type = 'expense'
                GROUP BY category
            """, (user_id,))
            return [dict(row) for row in cur.fetchall()]

    def get_hourly_pattern(self, user_id):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT strftime('%H', date) as hour,
                       COUNT(*) as count,
                       AVG(amount) as avg_amount
                FROM transactions
                WHERE user_id = ? AND type = 'expense'
                GROUP BY strftime('%H', date)
                ORDER BY hour
            """, (user_id,))
            return {row['hour']: float(row['avg_amount']) for row in cur.fetchall()}

# Ensure instance and logs folders exist
try:
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs('logs', exist_ok=True)
except Exception as e:
    print(f"Error creating directories: {e}")

# Single initialization block
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    try:
        setup_logging(app)
        if not os.path.exists(Config.DATABASE_PATH):
            print("Initializing database...")
            init_db()
            print("Database initialized successfully")
        app.logger.info("Financial application startup")
    except Exception as e:
        print(f"Startup error: {e}")
        raise

# Initialize repository after database setup and class definition
repo = TransactionRepository(Config.DATABASE_PATH)

@app.route('/')
def landing():
    if 'user_id' in session:
        return redirect(url_for('overview'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        app.logger.debug(f"Login attempt for username: {username}")
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login.html')
        
        try:
            user = repo.get_user_by_username(username)
            app.logger.debug(f"Found user: {user is not None}")
            
            if user and user.check_password(password):
                session.clear()
                session['user_id'] = user.id
                session['username'] = user.username
                session.permanent = True
                app.logger.info(f'User {user.username} logged in successfully')
                return redirect(url_for('overview'))
            else:
                app.logger.warning(f'Failed login attempt for username: {username}')
                flash('Invalid username or password', 'error')
        except Exception as e:
            app.logger.error(f'Login error: {str(e)}')
            flash('An error occurred during login', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if repo.add_user(User(
            username=request.form['username'],
            email=request.form['email'],
            password=request.form['password']
        )):
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/overview')
@login_required
def overview():
    try:
        transactions = repo.get_recent_transactions(session['user_id'], 30)
        monthly_summary = repo.get_monthly_summary(session['user_id'])
        
        # Get current month's data
        current_month = datetime.now().strftime('%Y-%m')
        current_month_data = next((item for item in monthly_summary if item['month'] == current_month), {
            'month': current_month,
            'income': 0,
            'expenses': 0
        })
        
        # Generate insights
        total_balance = repo.get_total_balance(session['user_id'])
        budgets = repo.get_budget_status(session['user_id'])
        insight_generator = InsightsGenerator(transactions, budgets, total_balance)
        insights = insight_generator.generate_insights()
        
        return render_template('overview.html',
                             active_page='overview',
                             transactions=transactions[:5],
                             total_balance=total_balance,
                             monthly_summary=monthly_summary,
                             current_month=current_month_data,
                             insights=insights)
    except Exception as e:
        app.logger.error(f'Error in overview page: {str(e)}')
        flash('An error occurred while loading the overview page.', 'error')
        session.clear()  # Clear session if there's an error
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('landing'))

@app.route('/transactions')
def transactions():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    transactions = repo.get_all(session['user_id'])
    categories = Transaction.CATEGORIES
    payment_methods = Transaction.PAYMENT_METHODS
    return render_template('transactions.html', 
                         active_page='transactions',
                         transactions=transactions,
                         categories=categories,
                         payment_methods=payment_methods)

@app.route('/budgets')
def budgets():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    budgets = repo.get_budget_status(session['user_id'])
    categories = Transaction.CATEGORIES
    return render_template('budgets.html', 
                         active_page='budgets',
                         budgets=budgets,
                         categories=categories)

@app.route('/add_budget', methods=['POST'])
@login_required
def add_budget():
    try:
        category = request.form.get('category')
        amount = float(request.form.get('amount', 0))
        period = request.form.get('period', 'monthly')
        alert_threshold = float(request.form.get('alert_threshold', 80.0))
        
        if not category or amount <= 0:
            flash('Please provide a valid category and amount', 'error')
            return redirect(url_for('budgets'))
        
        # Calculate start and end dates based on period
        today = datetime.now()
        start_date = today.replace(day=1).date()
        
        if period == 'monthly':
            end_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1).date() - timedelta(days=1)
        elif period == 'quarterly':
            quarter_end_month = ((today.month - 1) // 3 + 1) * 3
            end_date = today.replace(month=quarter_end_month, day=1)
            end_date = (end_date + timedelta(days=32)).replace(day=1).date() - timedelta(days=1)
        elif period == 'yearly':
            end_date = today.replace(month=12, day=31).date()
        else:
            flash('Invalid budget period', 'error')
            return redirect(url_for('budgets'))
        
        # Check for existing budget in the same category and period
        with repo.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id FROM budgets 
                WHERE user_id = ? AND category = ? 
                AND ((start_date BETWEEN ? AND ?) OR (end_date BETWEEN ? AND ?))
            """, (session['user_id'], category, start_date, end_date, start_date, end_date))
            
            if cur.fetchone():
                flash(f'A budget for {category} already exists in this period', 'error')
                return redirect(url_for('budgets'))
            
            # Add the new budget
            cur.execute("""
                INSERT INTO budgets (user_id, category, amount, period, start_date, end_date, alert_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], category, amount, period, start_date, end_date, alert_threshold))
            conn.commit()
            flash('Budget added successfully', 'success')
    except ValueError:
        flash('Please enter valid numeric values for amount and threshold', 'error')
    except Exception as e:
        app.logger.error(f'Error adding budget: {str(e)}')
        flash('Error adding budget', 'error')
    
    return redirect(url_for('budgets'))

@app.route('/savings')
def savings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        with repo.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, name, target_amount, current_amount, 
                       strftime('%Y-%m-%d', deadline) as deadline, status
                FROM savings_goals 
                WHERE user_id = ? AND status = 'active'
            """, (session['user_id'],))
            goals = [dict(row) for row in cur.fetchall()]
        return render_template('savings.html', 
                             active_page='savings',
                             goals=goals)
    except Exception as e:
        app.logger.error(f'Error loading savings goals: {str(e)}')
        flash('Error loading savings goals', 'error')
        return redirect(url_for('overview'))

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get last 30 days of transactions
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        transactions = repo.get_recent_transactions(session['user_id'], 30)
        
        # Calculate daily totals for last 4 days
        daily_totals = []
        for i in range(4):
            day = end_date - timedelta(days=i)
            total = sum(t.amount for t in transactions 
                       if t.type == 'expense' and t.date.date() == day.date())
            daily_totals.append({
                'date': day.strftime('%Y-%m-%d'),
                'amount': total
            })
        
        # Get category totals and other data
        category_data = repo.get_category_summary(session['user_id'])
        category_totals = {item['category']: float(item['total']) 
                          for item in category_data} if category_data else {}
        
        # Generate insights
        budgets = repo.get_budget_status(session['user_id'])
        total_balance = repo.get_total_balance(session['user_id'])
        insight_generator = InsightsGenerator(transactions, budgets, total_balance)
        insights = insight_generator.generate_insights()
        
        app.logger.info(f"Generated {len(insights)} insights for user {session['user_id']}")
        
        return render_template('analytics.html',
                             active_page='analytics',
                             insights=insights,
                             category_totals=category_totals,
                             daily_totals=daily_totals,
                             hourly_pattern=repo.get_hourly_pattern(session['user_id']),
                             debug_info={
                                 'transaction_count': len(transactions),
                                 'days_of_data': (end_date - start_date).days
                             })
    except Exception as e:
        app.logger.error(f"Analytics error: {str(e)}")
        return render_template('analytics.html',
                             active_page='analytics',
                             insights=[],
                             category_totals={},
                             daily_totals=[],
                             hourly_pattern={})

@app.route('/settings', methods=['GET'])
@login_required
def settings():
    try:
        user = repo.get_user_by_username(session.get('username'))
        currencies = ['USD', 'EUR', 'GBP', 'PHP']
        return render_template('settings.html',
                             active_page='settings',
                             user=user,
                             currencies=currencies)
    except Exception as e:
        app.logger.error(f'Settings error: {str(e)}')
        flash('Error loading settings', 'error')
        return redirect(url_for('overview'))

@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        try:
            transaction = Transaction(
                user_id=session['user_id'],
                date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
                description=request.form['description'],
                amount=float(request.form['amount']),
                category=request.form['category'],
                type=request.form['type'],
                payment_method=request.form['payment_method'],
                notes=request.form.get('notes', '')
            )
            repo.add(transaction)
            flash('Transaction added successfully', 'success')
            return redirect(url_for('transactions'))
        except Exception as e:
            app.logger.error(f'Error adding transaction: {str(e)}')
            flash('Error adding transaction', 'error')
    
    return render_template('add_transaction.html',
                         active_page='transactions',
                         categories=Transaction.CATEGORIES,
                         payment_methods=Transaction.PAYMENT_METHODS,
                         today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/edit_transaction/<int:id>', methods=['GET'])
@login_required
def edit_transaction(id):
    try:
        transaction = repo.get_by_id(id)
        if not transaction or transaction.user_id != session['user_id']:
            flash('Transaction not found', 'error')
            return redirect(url_for('transactions'))
        
        return render_template('edit_transaction.html',
                             active_page='transactions',
                             transaction=transaction,
                             categories=Transaction.CATEGORIES,
                             payment_methods=Transaction.PAYMENT_METHODS)
    except Exception as e:
        app.logger.error(f'Error editing transaction: {str(e)}')
        flash('Error loading transaction', 'error')
        return redirect(url_for('transactions'))

@app.route('/delete_transaction/<int:id>')
@login_required
def delete_transaction(id):
    try:
        transaction = repo.get_by_id(id)
        if transaction and transaction.user_id == session['user_id']:
            repo.delete(id)
            flash('Transaction deleted successfully', 'success')
        else:
            flash('Transaction not found', 'error')
    except Exception as e:
        app.logger.error(f'Error deleting transaction: {str(e)}')
        flash('Error deleting transaction', 'error')
    
    return redirect(url_for('transactions'))

@app.route('/update_transaction/<int:id>', methods=['POST'])
@login_required
def update_transaction(id):
    try:
        transaction = Transaction(
            id=id,
            user_id=session['user_id'],
            date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
            description=request.form['description'],
            amount=float(request.form['amount']),
            category=request.form['category'],
            type=request.form['type'],
            payment_method=request.form['payment_method'],
            notes=request.form.get('notes', '')
        )
        
        if repo.get_by_id(id).user_id == session['user_id']:
            repo.update(transaction)
            flash('Transaction updated successfully', 'success')
        else:
            flash('Transaction not found', 'error')
    except Exception as e:
        app.logger.error(f'Error updating transaction: {str(e)}')
        flash('Error updating transaction', 'error')
    
    return redirect(url_for('transactions'))

@app.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    try:
        settings = {
            'currency': request.form.get('currency', 'USD'),
            'notification_budget': request.form.get('notify_budget') == 'on',
            'notification_goals': request.form.get('notify_goals') == 'on'
        }
        
        if repo.update_user_settings(session['user_id'], settings):
            flash('Settings updated successfully', 'success')
        else:
            flash('Error updating settings', 'error')
    except Exception as e:
        app.logger.error(f'Settings update error: {str(e)}')
        flash('Error updating settings', 'error')
    
    return redirect(url_for('settings'))

@app.route('/edit_budget/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_budget(id):
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))
            alert_threshold = float(request.form.get('alert_threshold', 80))
            period = request.form.get('period')
            
            # Validate inputs
            if amount <= 0:
                flash('Budget amount must be greater than 0', 'error')
                return redirect(url_for('edit_budget', id=id))
            
            if alert_threshold < 1 or alert_threshold > 100:
                flash('Alert threshold must be between 1 and 100', 'error')
                return redirect(url_for('edit_budget', id=id))
            
            # Calculate dates based on period
            today = datetime.now()
            start_date = today.replace(day=1).date()
            
            if period == 'monthly':
                end_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1).date() - timedelta(days=1)
            elif period == 'quarterly':
                quarter_end_month = ((today.month - 1) // 3 + 1) * 3
                end_date = today.replace(month=quarter_end_month, day=1)
                end_date = (end_date + timedelta(days=32)).replace(day=1).date() - timedelta(days=1)
            elif period == 'yearly':
                end_date = today.replace(month=12, day=31).date()
            else:
                flash('Invalid budget period', 'error')
                return redirect(url_for('edit_budget', id=id))
            
            with repo.get_connection() as conn:
                cur = conn.cursor()
                # Check if another budget exists in the same category and period
                cur.execute("""
                    SELECT id FROM budgets 
                    WHERE user_id = ? AND category = (
                        SELECT category FROM budgets WHERE id = ? AND user_id = ?
                    ) AND id != ? 
                    AND ((start_date BETWEEN ? AND ?) OR (end_date BETWEEN ? AND ?))
                """, (session['user_id'], id, session['user_id'], id, start_date, end_date, start_date, end_date))
                
                if cur.fetchone():
                    flash('Another budget already exists in this period for the same category', 'error')
                    return redirect(url_for('edit_budget', id=id))
                
                # Update the budget
                cur.execute("""
                    UPDATE budgets 
                    SET amount = ?, alert_threshold = ?, period = ?, start_date = ?, end_date = ?
                    WHERE id = ? AND user_id = ?
                """, (amount, alert_threshold, period, start_date, end_date, id, session['user_id']))
                
                if cur.rowcount > 0:
                    conn.commit()
                    flash('Budget updated successfully', 'success')
                else:
                    flash('Budget not found', 'error')
            return redirect(url_for('budgets'))
            
        except ValueError:
            flash('Please enter valid numeric values', 'error')
        except Exception as e:
            app.logger.error(f'Error updating budget: {str(e)}')
            flash('Error updating budget', 'error')
        return redirect(url_for('edit_budget', id=id))
    
    try:
        with repo.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, category, amount, period, 
                       strftime('%Y-%m-%d', start_date) as start_date,
                       strftime('%Y-%m-%d', end_date) as end_date,
                       alert_threshold
                FROM budgets 
                WHERE id = ? AND user_id = ?
            """, (id, session['user_id']))
            budget = cur.fetchone()
            
            if budget:
                return render_template('edit_budget.html', 
                                     budget=dict(budget),
                                     periods=['monthly', 'quarterly', 'yearly'])
            flash('Budget not found', 'error')
    except Exception as e:
        app.logger.error(f'Error loading budget: {str(e)}')
        flash('Error loading budget', 'error')
    return redirect(url_for('budgets'))

@app.route('/delete_budget/<int:id>')
@login_required
def delete_budget(id):
    try:
        with repo.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM budgets 
                WHERE id = ? AND user_id = ?
            """, (id, session['user_id']))
            conn.commit()
            flash('Budget deleted successfully', 'success')
    except Exception as e:
        app.logger.error(f'Error deleting budget: {str(e)}')
        flash('Error deleting budget', 'error')
    return redirect(url_for('budgets'))

@app.route('/add_goal', methods=['POST'])
@login_required
def add_goal():
    try:
        name = request.form.get('name')
        target_amount = float(request.form.get('target_amount'))
        deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%d').date()
        
        if not name or target_amount <= 0:
            flash('Please provide valid goal details', 'error')
            return redirect(url_for('savings'))
        
        with repo.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO savings_goals (user_id, name, target_amount, current_amount, deadline, status)
                VALUES (?, ?, ?, 0, ?, 'active')
            """, (session['user_id'], name, target_amount, deadline))
            conn.commit()
            flash('Savings goal added successfully', 'success')
    except Exception as e:
        app.logger.error(f'Error adding savings goal: {str(e)}')
        flash('Error adding savings goal', 'error')
    
    return redirect(url_for('savings'))

@app.route('/edit_goal/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_goal(id):
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            target_amount = float(request.form.get('target_amount'))
            deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%d').date()
            
            with repo.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE savings_goals 
                    SET name = ?, target_amount = ?, deadline = ?
                    WHERE id = ? AND user_id = ?
                """, (name, target_amount, deadline, id, session['user_id']))
                conn.commit()
                flash('Goal updated successfully', 'success')
        except Exception as e:
            app.logger.error(f'Error updating goal: {str(e)}')
            flash('Error updating goal', 'error')
        return redirect(url_for('savings'))
    
    try:
        with repo.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, name, target_amount, current_amount, 
                       strftime('%Y-%m-%d', deadline) as deadline, status
                FROM savings_goals 
                WHERE id = ? AND user_id = ?
            """, (id, session['user_id']))
            goal = cur.fetchone()
            if goal:
                return render_template('edit_goal.html', goal=dict(goal))
            flash('Goal not found', 'error')
    except Exception as e:
        app.logger.error(f'Error loading goal: {str(e)}')
        flash('Error loading goal', 'error')
    return redirect(url_for('savings'))

@app.route('/delete_goal/<int:id>')
@login_required
def delete_goal(id):
    try:
        with repo.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM savings_goals 
                WHERE id = ? AND user_id = ?
            """, (id, session['user_id']))
            conn.commit()
            flash('Goal deleted successfully', 'success')
    except Exception as e:
        app.logger.error(f'Error deleting goal: {str(e)}')
        flash('Error deleting goal', 'error')
    return redirect(url_for('savings'))

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    try:
        with repo.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM transactions 
                WHERE user_id = ? 
                AND (description LIKE ? OR category LIKE ? OR notes LIKE ?)
                ORDER BY date DESC
                LIMIT 10
            """, (session['user_id'], f'%{query}%', f'%{query}%', f'%{query}%'))
            results = [Transaction.from_db_row(dict(row)) for row in cur.fetchall()]
            return jsonify([{
                'id': t.id,
                'date': t.date.strftime('%Y-%m-%d'),
                'description': t.description,
                'amount': float(t.amount),
                'category': t.category,
                'type': t.type
            } for t in results])
    except Exception as e:
        app.logger.error(f'Search error: {str(e)}')
        return jsonify([])

# Ensure proper shutdown handling
def shutdown_server():
    try:
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()
    except Exception as e:
        app.logger.error(f"Error shutting down: {e}")

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...'


# Update main block with better error handling
if __name__ == '__main__':
    try:
        app.run(host='127.0.0.1', port=5000)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Server stopped")
