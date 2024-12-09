from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from db import query_db, execute_db
import re
import hashlib

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def hash_password(pw):
    return hashlib.sha256(pw.encode('utf-8')).hexdigest()

def is_valid_username(username):
    # Adjust validation as needed - this simple regex checks alphanumeric plus underscores, length 3-20
    return re.match(r'^[A-Za-z0-9_]{3,20}$', username) is not None

def is_valid_email(email):
    # Basic email validation pattern
    return re.match(r'^[^@]+@[^@]+\.[^@]+$', email) is not None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()

        if not is_valid_username(username):
            flash("Invalid username format.", "error")
            return render_template('login.html')

        user = query_db("SELECT userName, password FROM Person WHERE userName=%s", (username,))
        if user and user[0]['password'] == hash_password(password):
            session['username'] = username
            flash("Logged in!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials.", "error")

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        confirm_password = request.form.get('confirm_password','').strip()
        fname = request.form.get('fname','').strip()
        lname = request.form.get('lname','').strip()
        email = request.form.get('email','').strip()

        # Validate inputs
        if not is_valid_username(username):
            flash("Invalid username format. Must be 3-20 alphanumeric chars.", "error")
            return render_template('register.html')
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template('register.html')
        if not is_valid_email(email):
            flash("Invalid email format.", "error")
            return render_template('register.html')

        # Check if username already exists
        existing_user = query_db("SELECT userName FROM Person WHERE userName=%s", (username,))
        if existing_user:
            flash("Username already taken. Please choose another one.", "error")
            return render_template('register.html')

        # Insert new user
        hashed_pw = hash_password(password)
        try:
            execute_db("INSERT INTO Person (userName, password, fname, lname, email) VALUES (%s, %s, %s, %s, %s)",
                       (username, hashed_pw, fname, lname, email))
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash("Database error: " + str(e), "error")
            return render_template('register.html')

    # GET request - show the registration form
    return render_template('register.html')

