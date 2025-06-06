# Personal Finance Management System

A secure and feature-rich financial management application built with Flask that helps users track expenses, manage budgets, and achieve savings goals.

## Features

- **Secure Authentication**
  - User registration and login
  - Admin dashboard with enhanced security
  - Password strength requirements
  - Brute force protection

- **Transaction Management**
  - Add, edit, and delete transactions
  - Categorize expenses
  - Multiple payment methods support
  - Search and filter capabilities

- **Budgeting**
  - Set budgets by category
  - Monthly, quarterly, and yearly budget periods
  - Alert thresholds for overspending
  - Visual budget progress tracking

- **Savings Goals**
  - Create and track savings targets
  - Deadline-based goal setting
  - Progress monitoring
  - Goal completion tracking

- **Analytics & Insights**
  - Spending pattern analysis
  - Category-wise breakdowns
  - Time-based summaries
  - Custom financial insights

## Setup Instructions

1. **Prerequisites**
   - Python 3.7+
   - SQLite3
   - pip package manager

2. **Installation**
   ```bash
   # Clone the repository
   git clone [repository-url]

   # Install dependencies
   pip install -r requirements.txt

   # Initialize the database
   python init_db.py
   ```

3. **First Time Setup**
   - Navigate to `/setup_admin` to create the admin account
   - Configure your environment variables in `config.py`
   - Set up logging directory

4. **Running the Application**
   ```bash
   python app.py
   ```

## Security Features

- Password hashing using bcrypt
- Session management
- CSRF protection
- Input validation
- SQL injection prevention
- Rate limiting on login attempts
- Secure password requirements

## Directory Structure

```
financial/
├── app.py              # Main application file
├── config.py           # Configuration settings
├── init_db.py          # Database initialization
├── models/             # Data models
├── routes/             # Route handlers
├── static/             # Static files (CSS, JS)
├── templates/          # HTML templates
└── logs/              # Application logs
```

## API Endpoints

- `/login` - User authentication
- `/register` - New user registration
- `/overview` - Dashboard view
- `/transactions` - Transaction management
- `/budgets` - Budget management
- `/savings` - Savings goals
- `/analytics` - Financial analytics
- `/admin/*` - Admin routes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please create an issue in the repository or contact the development team.

## Security Considerations

- Regular security updates are recommended
- Keep your admin credentials secure
- Monitor the logs for suspicious activity
- Regularly backup your database
- Use HTTPS in production

## Development

To set up the development environment:

```bash
# Create a virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Unix:
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt
```

## Testing

```bash
# Run tests
python -m pytest tests/

# Run with coverage
coverage run -m pytest
coverage report
```
