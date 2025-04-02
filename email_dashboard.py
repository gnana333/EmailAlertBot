from flask import Flask, render_template, redirect, url_for, request, jsonify, session
from pymongo import MongoClient
import pandas as pd
from datetime import datetime, timedelta
from collections import Counter
import bcrypt
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# MongoDB connection
cluster = MongoClient("mongodb+srv://kr4785543:1234567890@cluster0.220yz.mongodb.net/")
db = cluster["email_alert_bot"]
collection = db["emails"]
users_collection = db["users"]  # New collection for users

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('auth/login.html')
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = users_collection.find_one({'email': email})
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        session['user_id'] = str(user['_id'])
        session['email'] = user['email']
        session['name'] = user['name']
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('auth/register.html')
    
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    # Check if user already exists
    if users_collection.find_one({'email': email}):
        return jsonify({'success': False, 'message': 'Email already registered'}), 400

    # Hash password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Create new user
    user = {
        'name': name,
        'email': email,
        'password': hashed_password,
        'created_at': datetime.now()
    }
    
    users_collection.insert_one(user)
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get all emails from MongoDB
    emails = list(collection.find({'user_email': session['email']}).sort('timestamp', -1))
    
    # Convert to pandas DataFrame for easier analysis
    df = pd.DataFrame(emails)
    
    if df.empty:
        return render_template('email_dashboard.html', 
                             unique_keywords=set(),
                             email_count=0,
                             recent_emails=[],
                             user_stats=[],
                             keyword_data={},
                             user_name=session.get('name'))

    # 1. Keyword Statistics and Counts
    unique_keywords = set()
    keyword_counts = Counter()
    
    for email in emails:
        keywords = email.get('keywords', [])
        if keywords:
            for keyword in keywords:
                keyword_counts[keyword] += 1
                unique_keywords.add(keyword)

    keyword_data = {
        'labels': list(keyword_counts.keys()),
        'counts': list(keyword_counts.values())
    }

    # 2. Total Email Count
    email_count = len(emails)

    # 3. Recent Emails (last 10 emails)
    recent_emails = [
        {
            'text': email.get('email_text', '')[:100] + '...',
            'timestamp': email.get('timestamp', datetime.now()),
            'user_email': email.get('user_email', 'unknown')
        }
        for email in emails[:10]  # Only take the first 10 emails
    ]

    # 4. User Statistics
    user_stats = df.groupby('user_email').agg({
        '_id': 'count'
    }).reset_index().rename(columns={'_id': 'email_count'}).to_dict('records')

    return render_template('email_dashboard.html',
                         unique_keywords=sorted(unique_keywords),
                         email_count=email_count,
                         recent_emails=recent_emails,
                         user_stats=user_stats,
                         keyword_data=keyword_data,
                         user_name=session.get('name'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)

