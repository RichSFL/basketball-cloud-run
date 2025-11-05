"""Flask app for Cloud Run"""
from flask import Flask, jsonify
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "basketball-projections"}), 200

@app.route('/projections', methods=['GET'])
def projections():
    return jsonify({"message": "Projections endpoint", "data": []}), 200

if __name__ == '__main__':
    # This is only for local development
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
