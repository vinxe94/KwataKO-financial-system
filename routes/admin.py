from flask import Blueprint, render_template, redirect, url_for, request, flash, session, g, current_app
from functools import wraps
from models.user import User
import re
import sqlite3
from config import Config
import logging
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def get_db_connection():
    try:
        # Ensure the database file exists
        if not os.path.exists(Config.DATABASE_PATH):
            current_app.logger.error(f"Database file not found at {Config.DATABASE_PATH}")
            raise Exception("Database file not found")
            
        conn = sqlite3.connect(Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        current_app.logger.error(f"Database connection error: {e}")
        raise

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('Access denied: Admin privileges required', 'error')
            return redirect(url_for('login', type='admin'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT u.*, 
                       COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount 
                                        WHEN t.type = 'expense' THEN -t.amount 
                                        ELSE 0 END), 0) as balance
                FROM users u
                LEFT JOIN transactions t ON u.id = t.user_id
                WHERE u.is_admin = 0
                GROUP BY u.id, u.username, u.email
                ORDER BY u.username
            """)
            users = [dict(row) for row in cur.fetchall()]
            
        return render_template('admin/dashboard.html',
                             active_page='admin_dashboard',
                             users=users)
    except Exception as e:
        current_app.logger.error(f'Admin dashboard error: {str(e)}')
        flash('Error loading admin dashboard', 'error')
        return redirect(url_for('login'))

@admin_bp.route('/manage_users')
@admin_required
def manage_users():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT u.*, 
                       COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount 
                                        WHEN t.type = 'expense' THEN -t.amount 
                                        ELSE 0 END), 0) as balance
                FROM users u
                LEFT JOIN transactions t ON u.id = t.user_id
                WHERE u.is_admin = 0
                GROUP BY u.id, u.username, u.email
                ORDER BY u.username
            """)
            users = [dict(row) for row in cur.fetchall()]
            
        return render_template('admin/manage_users.html',
                             active_page='manage_users',
                             users=users)
    except Exception as e:
        current_app.logger.error(f'Error managing users: {str(e)}')
        flash('Error loading user management page', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/change_credentials', methods=['GET', 'POST'])
def change_credentials():
    try:
        if request.method == 'POST':
            current_password = request.form.get('current_password')
            new_username = request.form.get('new_username')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if not current_password:
                flash('Current password is required', 'error')
                return render_template('admin/change_credentials.html', active_page='change_credentials')
            
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                
                # Check if users table exists
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                if not cur.fetchone():
                    current_app.logger.error("Users table does not exist")
                    flash('Database not properly initialized', 'error')
                    return render_template('admin/change_credentials.html', active_page='change_credentials')
                
                # Check if is_admin column exists, if not add it
                cur.execute("PRAGMA table_info(users)")
                columns = [column[1] for column in cur.fetchall()]
                if 'is_admin' not in columns:
                    cur.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
                    # Set the first user as admin
                    cur.execute("UPDATE users SET is_admin = 1 WHERE id = 1")
                    conn.commit()
                
                # Get admin user
                cur.execute("SELECT * FROM users WHERE is_admin = 1 LIMIT 1")
                admin_user = cur.fetchone()
                
                if not admin_user:
                    # Create default admin if none exists
                    default_admin = User(
                        username='admin',
                        email='admin@example.com',
                        password='admin123',
                        is_admin=True
                    )
                    cur.execute("""
                        INSERT INTO users (username, email, password_hash, is_admin)
                        VALUES (?, ?, ?, 1)
                    """, (default_admin.username, default_admin.email, default_admin.password_hash))
                    conn.commit()
                    
                    cur.execute("SELECT * FROM users WHERE is_admin = 1 LIMIT 1")
                    admin_user = cur.fetchone()
                
                if not admin_user:
                    current_app.logger.error("Failed to create or retrieve admin user")
                    flash('Error accessing admin account', 'error')
                    return render_template('admin/change_credentials.html', active_page='change_credentials')
                
                user = User.from_db_row(dict(admin_user))
                
                # Verify current password
                if not user.check_password(current_password):
                    flash('Current password is incorrect', 'error')
                    return render_template('admin/change_credentials.html', active_page='change_credentials')
                
                # Verify new password if provided
                if new_password:
                    if new_password != confirm_password:
                        flash('New passwords do not match', 'error')
                        return render_template('admin/change_credentials.html', active_page='change_credentials')
                    
                    # Check password strength
                    if len(new_password) < 8:
                        flash('Password must be at least 8 characters long', 'error')
                        return render_template('admin/change_credentials.html', active_page='change_credentials')
                    if not re.search(r"[A-Z]", new_password):
                        flash('Password must contain at least one uppercase letter', 'error')
                        return render_template('admin/change_credentials.html', active_page='change_credentials')
                    if not re.search(r"[a-z]", new_password):
                        flash('Password must contain at least one lowercase letter', 'error')
                        return render_template('admin/change_credentials.html', active_page='change_credentials')
                    if not re.search(r"\d", new_password):
                        flash('Password must contain at least one number', 'error')
                        return render_template('admin/change_credentials.html', active_page='change_credentials')
                    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password):
                        flash('Password must contain at least one special character', 'error')
                        return render_template('admin/change_credentials.html', active_page='change_credentials')
                
                try:
                    # Update credentials
                    if new_username:
                        # Check if username is already taken by non-admin user
                        cur.execute("SELECT * FROM users WHERE username = ? AND id != ?", 
                                  (new_username, user.id))
                        if cur.fetchone():
                            flash('Username already taken', 'error')
                            return render_template('admin/change_credentials.html', active_page='change_credentials')
                        
                        cur.execute("UPDATE users SET username = ? WHERE id = ?",
                                  (new_username, user.id))
                    
                    if new_password:
                        user.set_password(new_password)
                        cur.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                                  (user.password_hash, user.id))
                    
                    conn.commit()
                    flash('Admin credentials updated successfully', 'success')
                    return redirect(url_for('landing'))
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    current_app.logger.error(f"Database error during update: {e}")
                    flash('Error updating credentials', 'error')
                    return render_template('admin/change_credentials.html', active_page='change_credentials')
                finally:
                    conn.close()
                    
            except sqlite3.Error as e:
                current_app.logger.error(f"Database error: {e}")
                flash('Database error occurred', 'error')
                return render_template('admin/change_credentials.html', active_page='change_credentials')
        
        return render_template('admin/change_credentials.html', active_page='change_credentials')
        
    except Exception as e:
        current_app.logger.error(f"Error in change_credentials: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return render_template('admin/change_credentials.html', active_page='change_credentials')

@admin_bp.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = bool(request.form.get('is_admin'))
        
        with get_db_connection() as conn:
            User.create_user(conn, username, email, password, is_admin)
            flash('User added successfully', 'success')
    except Exception as e:
        current_app.logger.error(f'Error adding user: {str(e)}')
        flash(f'Error adding user: {str(e)}', 'error')
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    try:
        User.toggle_user_status(g.db, user_id)
        flash('User status updated successfully', 'success')
    except Exception as e:
        flash(f'Error updating user status: {str(e)}', 'error')
    
    return redirect(url_for('admin.manage_users'))
