import os
import sqlite3
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta

app = Flask(__name__)

# --- CONFIGURATION ---
# n8n-la irunthu kidaikkura Webhook URL-ai inge paste pannunga
N8N_WEBHOOK_URL = "http://localhost:5678/webhook-test/internship-reminder"

# --- DATABASE SETUP ---
def get_db_connection():
    # Database name unga code-padi 'internships.db'
    conn = sqlite3.connect('internships.db')
    conn.row_factory = sqlite3.Row # Ithu mukkiam! Row objects-ah edukkum
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS applications 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     email TEXT, company TEXT, role TEXT, 
                     platform TEXT, date_applied TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- SCHEDULER LOGIC ---
scheduler = APScheduler()

def check_and_send_reminders():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"Checking for internships starting on: {tomorrow}")

    conn = get_db_connection()
    reminders = conn.execute('SELECT * FROM applications WHERE date_applied = ?', (tomorrow,)).fetchall()
    conn.close()

    for row in reminders:
        payload = {
            "email": row['email'],
            "company": row['company'],
            "role": row['role'],
            "platform": row['platform'],
            "date": row['date_applied'],
            "reminder_type": "One Day Before"
        }
        try:
            requests.post(N8N_WEBHOOK_URL, json=payload)
            print(f"Sent reminder for {row['company']} to n8n")
        except Exception as e:
            print(f"Error sending to n8n: {e}")

# Dhinamum kaalai 8:00 AM-kku automate aagum
scheduler.add_job(id='Daily_Job', func=check_and_send_reminders, trigger='cron', hour=8, minute=0)
scheduler.start()

# --- ROUTES ---

@app.route('/')
def index():
    conn = get_db_connection()
    # Data-vai 'apps' nu pass panrom, HTML-la ithu thaan loop aagum
    apps = conn.execute('SELECT * FROM applications ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('index.html', apps=apps)

@app.route('/add', methods=['POST'])
def add_entry():
    email = request.form['email']
    company = request.form['company']
    role = request.form['role']
    platform = request.form['platform']
    date = request.form['date'] 
    
    conn = get_db_connection()
    conn.execute('INSERT INTO applications (email, company, role, platform, date_applied) VALUES (?, ?, ?, ?, ?)',
                 (email, company, role, platform, date))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# --- DELETE ROUTE (NEWLY ADDED & FIXED) ---
@app.route('/delete/<int:id>')
def delete_entry(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM applications WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/get-reminders', methods=['GET'])
def get_reminders():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    conn = get_db_connection()
    reminders = conn.execute('SELECT * FROM applications WHERE date_applied = ?', (tomorrow,)).fetchall()
    conn.close()
    
    result = [dict(r) for r in reminders]
    return jsonify(result)

if __name__ == '__main__':
    # use_reloader=False mukkiam, illana scheduler rendu thadava run aagum
    app.run(debug=True, use_reloader=False)