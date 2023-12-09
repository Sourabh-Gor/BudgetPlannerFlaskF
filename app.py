from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
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

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget.db'
db = SQLAlchemy(app)
monthly_budget = 0
expenses = []

app.config['SECRET_KEY'] = 'your_secret_key'
app.config['MAIL_SERVER'] = 'smtp.yourmailprovider.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'your_email@example.com'
app.config['MAIL_PASSWORD'] = 'your_email_password'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # Use SQLite for simplicity


mail = Mail(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)

@app.route('/')
def trw():
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
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')


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


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        name = request.form['name']

        user = User.query.filter_by(name=name).first()

        if user:
            reset_token = generate_reset_token()
            send_reset_email(user.name, user.email, reset_token)

            flash('Password reset email sent. Please check your email.', 'success')
            return redirect(url_for('login'))

        else:
            flash('User not found. Please check the entered username.', 'error')

    return render_template('forgot_password.html')


def generate_reset_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=30))


def send_reset_email(username, email, token):
    reset_link = url_for('reset_password', username=username, token=token, _external=True)
    subject = 'Password Reset Request'
    body = f"Hi {username},\n\nTo reset your password, click the following link:\n{reset_link}"

    msg = Message(subject, sender='your_email@example.com', recipients=[email])
    msg.body = body

    mail.send(msg)


@app.route('/expenses')
def home():
    return render_template('index.html', budget=monthly_budget, expenses=expenses)

@app.route('/budget')
def xyz():
    budgets = Budget.query.all()
    return render_template('monthlybudget.html',budgets=budgets)



@app.route('/add_budget', methods=['POST'])
def add_budget():
    amount = request.form.get('amount')

    if amount:
        new_budget = Budget(amount=amount)
        db.session.add(new_budget)
        db.session.commit()

    return redirect(url_for('budget'))

@app.route('/update_budget/<int:budget_id>', methods=['GET', 'POST'])
def update_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)

    if request.method == 'POST':
        new_amount = request.form.get('amount')
        budget.amount = new_amount
        db.session.commit()
        return redirect(url_for('budget'))

    return render_template('update_budget.html', budget=budget)

@app.route('/delete_budget/<int:budget_id>')
def delete_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    db.session.delete(budget)
    db.session.commit()
    return redirect(url_for('budget'))

@app.route('/set_budget', methods=['POST'])
def set_budget():
    global monthly_budget
    monthly_budget = float(request.form['budget'])
    return redirect(url_for('home'))

@app.route('/add_expense', methods=['POST'])
def add_expense():
    expense = float(request.form['expense'])
    expenses.append(expense)
    return redirect(url_for('home'))

@app.route('/calculate_result')
def calculate_result():
    total_expenses = sum(expenses)
    remaining_budget = monthly_budget - total_expenses
    return render_template('result.html', budget=monthly_budget, expenses=expenses, total_expenses=total_expenses, remaining_budget=remaining_budget, sum=sum)



@app.route('/report')
def plot_expenses():
    # Create a bar plot of expenses
    fig, ax = plt.subplots()
    ax.plot(range(1, len(expenses) + 1), expenses, color='blue')
    ax.scatter(range(1, len(expenses) + 1), expenses, color='blue')
    ax.set_xlabel('Expense')
    ax.set_ylabel('Amount')
    ax.set_title('Monthly Expenses')

    # Save the plot to a BytesIO object
    image_stream = io.BytesIO()
    plt.savefig(image_stream, format='png')
    image_stream.seek(0)

    # Encode the plot image as base64
    encoded_image = base64.b64encode(image_stream.read()).decode('utf-8')

    return render_template('plot_expenses.html', image=encoded_image)



@app.route('/generate_report')
def generate_report():
    # For demonstration purposes, let's assume the user is logged in
    # Replace this with your actual authentication logic

    # Get the user's name (you might need to modify this based on your authentication mechanism)
    user_name = "John Doe"  # Replace this with the actual user's name

    # Generate the PDF content
    pdf_content = generate_pdf_content(user_name)

    # Rewind the BytesIO object to the beginning
    pdf_content.seek(0)

    # Serve the PDF file
    return send_file(
        io.BytesIO(pdf_content.read()),
        as_attachment=True,
        download_name='budget_report.pdf',
        mimetype='application/pdf'
    )
def generate_pdf_content(user_name):
    # Create a PDF document using reportlab
    pdf_buffer = io.BytesIO()
    pdf = canvas.Canvas(pdf_buffer)

    # Add content to the PDF
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 750, f"{user_name}'s Budget Planner Report")
    pdf.drawString(100, 730, "Additional content can be added here.")

    # Add the graph to the PDF
    graph_image = generate_plot_image()
    pdf.drawImage(graph_image, x=100, y=500, width=400, height=300)

    # Save the PDF to the buffer
    pdf.showPage()
    pdf.save()

    # Reset the buffer position to the beginning
    pdf_buffer.seek(0)

    return pdf_buffer

def generate_plot_image():
    # Create a bar plot of expenses
    fig, ax = plt.subplots()
    ax.plot(range(1, len(expenses) + 1), expenses, color='blue')
    ax.scatter(range(1, len(expenses) + 1), expenses, color='blue')
    ax.set_xlabel('Expense')
    ax.set_ylabel('Amount')
    ax.set_title('Monthly Expenses')

    # Save the plot to a BytesIO object
    image_stream = io.BytesIO()
    plt.savefig(image_stream, format='png')
    image_stream.seek(0)

    # Return the BytesIO object
    return image_stream

@app.route('/reset_password/<username>/<token>', methods=['GET', 'POST'])
def reset_password(username, token):
    if request.method == 'POST':
        new_password = request.form['new_password']
        # Update the user's password in the database
        user = User.query.filter_by(name=username).first()
        if user:
            user.password = new_password
            db.session.commit()
            flash('Password reset successful! Please login with your new password.', 'success')
            return redirect(url_for('login'))

    return render_template('reset_password.html', username=username, token=token)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)



