"""Flask app for Cloud Run"""
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "basketball-projections"}), 200

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "API is working"}), 200

# gunicorn looks for 'app' variable
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
