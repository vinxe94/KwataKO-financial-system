from datetime import datetime, timedelta
from collections import defaultdict

class InsightsGenerator:
    def __init__(self, transactions, budget_status, total_balance):
        self.transactions = transactions
        self.budget_status = budget_status
        self.total_balance = total_balance

    def format_currency(self, amount):
        return "${:,.2f}".format(amount)

    def generate_insights(self):
        insights = []
        
        # Basic insights that don't require much data
        expense_transactions = [t for t in self.transactions if t.type == 'expense']
        income_transactions = [t for t in self.transactions if t.type == 'income']
        
        total_expenses = sum(t.amount for t in expense_transactions)
        total_income = sum(t.amount for t in income_transactions)
        
        # Income insights
        if income_transactions:
            income_by_category = defaultdict(float)
            income_counts = defaultdict(int)
            for t in income_transactions:
                income_by_category[t.category] += t.amount
                income_counts[t.category] += 1
            
            if income_by_category:
                highest_income = max(income_by_category.items(), key=lambda x: x[1])
                avg_income = highest_income[1] / income_counts[highest_income[0]]
                insights.append({
                    'type': 'success',
                    'message': f'Your main source of income is {highest_income[0]} ({self.format_currency(highest_income[1])}, averaging {self.format_currency(avg_income)} per payment)'
                })
        
        # Balance insights
        if self.total_balance < 0:
            insights.append({
                'type': 'danger',
                'message': f'Your balance is negative ({self.format_currency(self.total_balance)}). Consider reducing expenses or increasing income.'
            })
        elif self.total_balance < total_expenses * 0.5:
            insights.append({
                'type': 'warning',
                'message': f'Your balance ({self.format_currency(self.total_balance)}) is low compared to your expenses. Aim to maintain at least 3 months of expenses in savings.'
            })
        elif self.total_balance > total_expenses * 3:
            insights.append({
                'type': 'success',
                'message': f'Great job! You have a healthy emergency fund of {self.format_currency(self.total_balance)}.'
            })

        # Expense insights
        if expense_transactions:
            # Category breakdown for expenses only
            expense_by_category = defaultdict(float)
            expense_counts = defaultdict(int)
            for t in expense_transactions:
                expense_by_category[t.category] += t.amount
                expense_counts[t.category] += 1
            
            # Find highest expense category
            if expense_by_category:
                highest_expense = max(expense_by_category.items(), key=lambda x: x[1])
                avg_expense = highest_expense[1] / expense_counts[highest_expense[0]]
                insights.append({
                    'type': 'info',
                    'message': f'Your highest expense category is {highest_expense[0]} ({self.format_currency(highest_expense[1])}, avg {self.format_currency(avg_expense)} per transaction)'
                })

                # Identify significant expense categories
                for category, amount in expense_by_category.items():
                    if amount > total_expenses * 0.4:  # If category is more than 40% of total expenses
                        insights.append({
                            'type': 'warning',
                            'message': f'Your {category} expenses represent {amount/total_expenses:.0%} of your total spending'
                        })

        # Income vs Expenses insights
        if total_income > 0:
            expense_ratio = total_expenses / total_income
            savings_ratio = 1 - expense_ratio
            if expense_ratio > 0.9:
                insights.append({
                    'type': 'danger',
                    'message': f'You are spending {expense_ratio:.0%} of your income. Consider reducing expenses.'
                })
            elif expense_ratio < 0.5:
                insights.append({
                    'type': 'success',
                    'message': f'Excellent! You are saving {savings_ratio:.0%} of your income. Keep up the good work!'
                })
            elif expense_ratio < 0.7:
                insights.append({
                    'type': 'info',
                    'message': f'You are saving {savings_ratio:.0%} of your income. Consider increasing your savings rate.'
                })

        # Budget insights
        if self.budget_status:
            for budget in self.budget_status:
                if budget['progress'] >= 100:
                    insights.append({
                        'type': 'danger',
                        'message': f'You have exceeded your {budget["category"]} budget by {self.format_currency(budget["spent"] - budget["amount"])}.'
                    })
                elif budget['progress'] >= 90:
                    insights.append({
                        'type': 'warning',
                        'message': f'You are close to exceeding your {budget["category"]} budget ({self.format_currency(budget["amount"] - budget["spent"])} remaining).'
                    })
                elif budget['progress'] <= 30 and budget['amount'] > 0:
                    insights.append({
                        'type': 'success',
                        'message': f'You are well within your {budget["category"]} budget ({self.format_currency(budget["amount"] - budget["spent"])} remaining).'
                    })

        # Recent spending insights
        if len(expense_transactions) >= 5:
            recent_transactions = [t for t in expense_transactions if t.date >= datetime.now() - timedelta(days=7)]
            if recent_transactions:
                avg_daily = sum(t.amount for t in recent_transactions) / 7
                if avg_daily > total_expenses / 30:  # If daily average is higher than monthly average
                    insights.append({
                        'type': 'warning',
                        'message': f'Your daily spending ({self.format_currency(avg_daily)}) is higher than your monthly average. Consider reducing daily expenses.'
                    })

        # If no insights generated, add a basic one
        if not insights:
            insights.append({
                'type': 'info',
                'message': 'Add more transactions to get detailed financial insights.'
            })

        return insights
