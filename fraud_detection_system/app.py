from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
from authlib.integrations.flask_client import OAuth
import subprocess
import os
import json
import pandas as pd
import io

app = Flask(__name__)
# Use environment variable for Secret Key (with fallback)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod-8237')

# Use environment variable for Database URL (Render provides DATABASE_URL)
# Fallback to local sqlite
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    # Explicitly use the instance folder for the database
    db_path = os.path.join(app.instance_path, 'users.db')
    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    db_url = f'sqlite:///{db_path}'

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1) # SQLAlchemy fix for Render
app.config['SQLALCHEMY_DATABASE_URI'] = db_url

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- OAuth Setup ---
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# --- Database Models ---

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    # Relationship: One user has many history items
    history = db.relationship('TransactionHistory', backref='user', lazy=True)

class TransactionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # Store the raw input the user typed
    input_data = db.Column(db.Text, nullable=False)
    # Store the full JSON result from the C++ engine
    analysis_result = db.Column(db.Text, nullable=False)
    # Store quick stats for display
    fraud_count = db.Column(db.Integer, default=0)
    total_items = db.Column(db.Integer, default=0)
    # Foreign Key: Links this row to a User ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Determine Engine Path based on OS
if os.name == 'nt': # Windows
    ENGINE_FILENAME = 'fraud_engine.exe'
else: # Linux/Mac
    ENGINE_FILENAME = 'fraud_engine'

ENGINE_PATH = os.path.join(os.getcwd(), ENGINE_FILENAME)

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login Failed. Check username and password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
            
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    csv_input = ""
    raw_input_storage = ""

    # Check for File Upload (multipart/form-data) or JSON
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        if 'file' not in request.files:
             return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        if file.filename == '':
             return jsonify({"error": "No selected file"}), 400
             
        try:
            # Read CSV with Pandas
            df = pd.read_csv(file)
            
            # --- Data Cleaning & Normalization ---
            # Standardize headers
            df.columns = df.columns.str.strip().str.lower()
            
            # Prepare target structure
            expected_cols = ['id', 'amount', 'description', 'time', 'payment_mode']
            final_df = pd.DataFrame()
            
            # Intelligent Column Mapping
            for target in expected_cols:
                # 1. Exact match
                if target in df.columns:
                    final_df[target] = df[target]
                else:
                    # 2. Fuzzy/Keyword match
                    match = next((c for c in df.columns if target in c), None)
                    if match:
                         final_df[target] = df[match]
                    else:
                        # 3. Defaults
                        if target == 'amount': final_df[target] = 0.0
                        elif target == 'time': final_df[target] = datetime.now().strftime("%H:%M")
                        elif target == 'payment_mode': final_df[target] = "Unknown"
                        else: final_df[target] = "N/A" # id, description

            # Clean Values
            final_df['amount'] = pd.to_numeric(final_df['amount'], errors='coerce').fillna(0.0)
            final_df.fillna("Unknown", inplace=True)
            
            # Generate CSV string for C++ Engine (No Header)
            csv_input = final_df.to_csv(index=False, header=False)
            
            # Store summary for history
            raw_input_storage = f"File Upload: {file.filename} ({len(df)} transactions)"
            
        except Exception as e:
            return jsonify({"error": f"CSV Processing Error: {str(e)}"}), 500

    else:
        # JSON / Manual Text Input
        data = request.json.get('data', '')
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Parse manual lines and pad to 5 columns
        lines = data.strip().split('\n')
        processed_lines = []
        for line in lines:
            if not line.strip(): continue
            parts = [p.strip() for p in line.split(',')]
            
            # Ensure at least ID, Amount, Desc
            if len(parts) >= 3:
                # Pad Time
                if len(parts) < 4: parts.append(datetime.now().strftime("%H:%M"))
                # Pad Payment Mode
                if len(parts) < 5: parts.append("Manual")
                
                processed_lines.append(",".join(parts))
        
        csv_input = "\n".join(processed_lines)
        raw_input_storage = data

    try:
        # Run the C++ executable
        process = subprocess.Popen(
            [ENGINE_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Pass the formatted CSV data to the C++ engine
        stdout, stderr = process.communicate(input=csv_input)
        
        if process.returncode != 0:
            return jsonify({"error": f"Engine Error: {stderr}"}), 500
            
        # Parse the JSON output from the C++ engine
        try:
            result = json.loads(stdout)
            
            # --- SAVE TO DATABASE ---
            fraud_detected = sum(1 for t in result if t.get('is_suspicious', False))
            
            new_history = TransactionHistory(
                input_data=raw_input_storage,
                analysis_result=json.dumps(result),
                fraud_count=fraud_detected,
                total_items=len(result),
                user=current_user
            )
            
            db.session.add(new_history)
            db.session.commit()
            # ------------------------

            return jsonify(result)
        except json.JSONDecodeError:
             return jsonify({"error": "Invalid output from engine", "raw_output": stdout}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- NEW HISTORY ROUTES ---

@app.route('/get_history')
@login_required
def get_history():
    # Fetch latest 50 items for this user, newest first
    items = TransactionHistory.query.filter_by(user_id=current_user.id)\
        .order_by(TransactionHistory.timestamp.desc())\
        .limit(50).all()
    
    # Format for JSON response
    history_data = []
    for item in items:
        history_data.append({
            "id": item.id,
            "date": item.timestamp.strftime('%Y-%m-%d'),
            "timestamp": item.timestamp.strftime('%H:%M:%S'),
            "input": item.input_data,
            # We stored it as a string, so we load it back to a list
            "results": json.loads(item.analysis_result),
            "fraudCount": item.fraud_count,
            "total": item.total_items
        })
    return jsonify(history_data)

@app.route('/clear_history', methods=['POST'])
@login_required
def clear_history():
    # Delete all history for current user
    TransactionHistory.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"success": True})

# --- OAuth Routes ---

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_auth', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google')
def google_auth():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        # User info contains 'email', 'name', 'picture' etc.
        email = user_info['email']
        
        # Logic: Check if user exists by email (using email as username for now)
        user = User.query.filter_by(username=email).first()
        
        if not user:
            # Create a new user automatically
            # We set a random password because they won't use it (they use Google)
            random_password = bcrypt.generate_password_hash(os.urandom(16)).decode('utf-8')
            user = User(username=email, password=random_password)
            db.session.add(user)
            db.session.commit()
            
        login_user(user)
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f"Google Login Failed: {str(e)}", "danger")
        return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)