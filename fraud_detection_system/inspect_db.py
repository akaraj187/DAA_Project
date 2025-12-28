from app import app, db, User, TransactionHistory
import sqlite3
import os

db_file = 'instance/users.db' # Flask-SQLAlchemy usually puts it here in later versions
if not os.path.exists(db_file):
    db_file = 'users.db' # fallback to root

print(f"Checking database at: {db_file}")

with app.app_context():
    # Ensure tables exist before querying (Fixes 'no such table' error)
    db.create_all()
    
    print("\n--- Users in Database ---")
    users = User.query.all()
    for u in users:
        print(f"ID: {u.id} | Username: {u.username}")
        
    print("\n--- History in Database ---")
    history = TransactionHistory.query.all()
    if not history:
        print("No history entries found.")
    for h in history:
        print(f"ID: {h.id} | UserID: {h.user_id} | Items: {h.total_items} | Fraud: {h.fraud_count} | Date: {h.timestamp}")
        # print(f"  Data: {h.input_data[:50]}...") # Show first 50 chars of input

print("\n--- Raw Table Check ---")
if os.path.exists(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print(f"Tables found: {[t[0] for t in cursor.fetchall()]}")
    conn.close()