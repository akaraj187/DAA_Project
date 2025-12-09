from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import subprocess
import os
import json

app = Flask(__name__)
# Use environment variable for Secret Key (with fallback)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod-8237')

# Use environment variable for Database URL (Render provides DATABASE_URL)
# Fallback to local sqlite
db_url = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1) # SQLAlchemy fix for Render
app.config['SQLALCHEMY_DATABASE_URI'] = db_url

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Determine Engine Path based on OS
if os.name == 'nt': # Windows
    ENGINE_FILENAME = 'fraud_engine.exe'
else: # Linux/Mac
    ENGINE_FILENAME = 'fraud_engine'

ENGINE_PATH = os.path.join(os.getcwd(), ENGINE_FILENAME)

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
    # Get raw text from the request
    data = request.json.get('data', '')
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Run the C++ executable
        process = subprocess.Popen(
            [ENGINE_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Pass the data to the C++ engine
        stdout, stderr = process.communicate(input=data)
        
        if process.returncode != 0:
            return jsonify({"error": f"Engine Error: {stderr}"}), 500
            
        # Parse the JSON output from the C++ engine
        # The C++ engine prints JSON to stdout
        try:
            result = json.loads(stdout)
            return jsonify(result)
        except json.JSONDecodeError:
             return jsonify({"error": "Invalid output from engine", "raw_output": stdout}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
