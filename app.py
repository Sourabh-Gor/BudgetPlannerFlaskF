from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import io
import base64
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import os
import random
import string
from reportlab.pdfgen import canvas
from flask import send_file
import tempfile
from datetime import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # Use SQLite for simplicity

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User model with UserMixin for Flask-Login
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    amount = db.Column(db.Float, default=0.0, nullable=False)
    expenses = db.relationship('Expense', backref='user', lazy=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    print(current_user.is_authenticated)
    return render_template('base.html')

@app.route('/view_users')
def view_users():
    users = User.query.all()
    return render_template('view_users.html', users=users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        user = User.query.filter_by(name=name, password=password).first()

        if user:
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        email = request.form['email']

        new_user = User(name=name, password=password, email=email)
        db.session.add(new_user)
        db.session.commit()

        flash('Signup successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')



@app.route('/budget')
@login_required
def budget():
    return render_template('monthlybudget.html', budget=current_user.amount)



# Add a check in add_budget to prevent creating multiple budgets for the same user
@app.route('/add_budget', methods=['POST'])
@login_required
def add_budget():
    # Check if the user already has a budget
    print(f"Current User Amount: {current_user.amount}")

    # if current_user.amount is not None:
    #     flash('You already have a budget. To update it, please use the update page.', 'warning')
    #     return redirect(url_for('budget'))

    amount = request.form.get('amount')
    print(f"Amount from Form: {amount}")

    if amount:
        current_user.amount = amount
        db.session.commit()
        print("Budget added successfully")

    print(f"Updated Current User Amount: {current_user.amount}")

    return redirect(url_for('budget'))





@app.route('/update_budget/', methods=['GET', 'POST'])
@login_required
def update_budget():
    if request.method == 'POST':
        new_amount = request.form.get('amount')
        current_user.amount = new_amount
        db.session.commit()
        return redirect(url_for('budget'))

    return render_template('update.html', budget=current_user.amount)


@app.route('/delete_budget')
@login_required
def delete_budget():
    current_user.amount = 0.0  # Set the budget to zero (or any default value)
    db.session.commit()
    return redirect(url_for('budget'))

@app.route('/expenses')
@login_required
def expenses():
    expenses = Expense.query.filter_by(user_id=current_user.id)
    return render_template('expenses.html', expenses=expenses, budget=current_user.amount)

# Create a new expense and add it to the database
@app.route('/add_expense', methods=['POST'])
@login_required
def add_expense():
    try:
        amount = float(request.form.get('amount'))
    except (ValueError, TypeError):
        return redirect(url_for('expenses'))

    description = request.form.get('description')

    if not description or amount is None:
        return redirect(url_for('expenses'))

    expense = Expense(description=description, amount=amount, user_id=current_user.id)
    db.session.add(expense)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()

    return redirect(url_for('expenses'))


# Update an existing expense in the database
@app.route("/edit_expense/<int:expense_id>", methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)

    if request.method == 'POST':
        description = request.form.get('description')
        amount = request.form.get('amount')

        if not description or not amount:
            return redirect(url_for('expenses'))

        expense.description = description
        expense.amount = amount
        db.session.commit()

        return redirect(url_for('expenses'))

    return render_template('edit_expense.html', expense=expense)

# Delete an expense from the database
@app.route('/delete_expense/<int:expense_id>', methods=['GET'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('expenses'))


from flask import render_template

@app.route('/calculate_result')
@login_required
def calculate_result():
    # Fetch expenses for the current user
    expenses = Expense.query.filter_by(user_id=current_user.id).all()

    # Fetch the budget for the current user
    budget = current_user.amount

    # Calculate total expenses
    total_expenses = sum(expense.amount for expense in expenses)

    # Calculate remaining budget
    remaining_budget = budget - total_expenses

    return render_template('result.html', budget=budget, expenses=expenses, total_expenses=total_expenses, remaining_budget=remaining_budget)

@app.route('/report')
@login_required
def plot_chart():
    expenses = Expense.query.filter_by(user_id=current_user.id)
    x = [expense.description for expense in expenses]
    y = [expense.amount for expense in expenses]
    fig, ax = plt.subplots()
    ax.pie(y, labels=x, autopct='%1.1f%%')
    ax.set_title('Expenses')
    ax.axis('equal')
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    image_base64 = base64.b64encode(img.getvalue()).decode('utf-8')
    return render_template('plot_expenses.html', image=image_base64)


from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import datetime

# @app.route("/download")
# @login_required
# def download_pdf():
#     # Create a PDF object
#     pdf = canvas.Canvas("report.pdf")

#     # Draw things on the PDF. Here's where the PDF generation happens.
#     # See the ReportLab documentation for the full list of functionality.
#     pdf.setFont("Helvetica", 12)
#     pdf.drawString(100, 750, f"{current_user.name}'s Budget Planner Report")
#     pdf.drawString(100, 730, "Additional content can be added here.")

#     # Close the PDF object cleanly, and we're done.
#     pdf.showPage()
#     pdf.save()

#     return redirect(url_for('expenses'))

import io
import os
from flask import Flask, send_file
from reportlab.pdfgen import canvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import tempfile


@app.route('/generate_report')
def generate_report():
    # For demonstration purposes, let's assume the user is logged in
    # Replace this with your actual authentication logic

    # Get the user's name (you might need to modify this based on your authentication mechanism)
      # Replace this with the actual user's name

    # Generate the PDF content
    pdf_content = generate_pdf_content(current_user.name)

    # Rewind the BytesIO object to the beginning
    pdf_content.seek(0)

    # Serve the PDF file as an attachment for download
    return send_file(
        pdf_content,
        as_attachment=True,
        download_name='budget_report.pdf',
        mimetype='application/pdf'
    )

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
def generate_pdf_content(user_name):
    # Create a PDF document using reportlab
    pdf_buffer = io.BytesIO()
    pdf = SimpleDocTemplate(pdf_buffer, pagesize=letter)

    # Content for the PDF
    content = []

    # Add title
    title_style = ParagraphStyle(
        'TitleWithBorder',
        parent=getSampleStyleSheet()['Title'],
        borderPadding=(10, 5, 5, 5),
        borderColor=colors.black,
        borderWidth=1,
    )
    title_text = f"{user_name}'s Budget Planner Report"
    content.append(Paragraph(title_text, title_style))
    # Add expenses details
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    if expenses:
        content.append(Spacer(1, 12))  # Add some space

        expense_heading_style = ParagraphStyle(
            'ExpenseHeading',
            parent=getSampleStyleSheet()['Heading1'],
        )
        expense_heading_text = "Expenses Details"
        content.append(Paragraph(expense_heading_text, expense_heading_style))

        for expense in expenses:
            expense_style = getSampleStyleSheet()['BodyText']
            expense_text = f"<b>Description:</b> {expense.description}<br/>" \
                           f"<b>Amount:</b> {expense.amount}<br/>" \
                           f"<b>Date:</b> {expense.date}<br/>"
            content.append(Paragraph(expense_text, expense_style))

    # Add budget
    budget = current_user.amount  # Replace with the actual budget value
    budget_style = getSampleStyleSheet()['BodyText']
    budget_text = f"<br/><b>Budget:</b> {budget}"
    content.append(Paragraph(budget_text, budget_style))


    # Save the Matplotlib plot to a BytesIO buffer
    img_buffer = io.BytesIO()
    expenses = Expense.query.filter_by(user_id=current_user.id)
    x = [expense.description for expense in expenses]
    y = [expense.amount for expense in expenses]
    fig, ax = plt.subplots()
    ax.pie(y, labels=x, autopct='%1.1f%%')
    ax.set_title('Expenses')
    ax.axis('equal')
    fig.savefig(img_buffer, format='png')
    img_buffer.seek(0)

    # Add the Matplotlib plot as an Image to the PDF
    img = Image(img_buffer, width=400, height=300)
    content.append(img)

    # Build the PDF document
    pdf.build(content)

    # Reset the buffer position to the beginning
    pdf_buffer.seek(0)

    return pdf_buffer


def save_plot_to_tempfile():
    # Generate a sample plot using Matplotlib
    expenses = Expense.query.filter_by(user_id=current_user.id)
    x = [expense.description for expense in expenses]
    y = [expense.amount for expense in expenses]
    fig, ax = plt.subplots()
    ax.pie(y, labels=x, autopct='%1.1f%%')
    ax.set_title('Expenses')
    ax.axis('equal')
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)

    # Save the Matplotlib plot to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    temp_file_path = temp_file.name
    canvas = FigureCanvas(fig)
    canvas.print_png(temp_file_path)
    temp_file.close()

    return temp_file_path


if __name__ == '__main__':
    # Ensure the app uses the port specified by Render
    port = int(os.environ.get('PORT', 5000))  # Use 5000 as a default for local development
    with app.app_context():
        db.create_all()   # Create the database tables
    app.run(host='0.0.0.0', port=port, debug=True)
