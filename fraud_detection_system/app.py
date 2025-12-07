from flask import Flask, render_template, request, jsonify
import subprocess
import os
import json

app = Flask(__name__)

# Path to the compiled C++ executable
ENGINE_PATH = os.path.join(os.getcwd(), 'fraud_engine.exe')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
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
    app.run(debug=True, port=5000)
