from flask import Flask, redirect, url_for
import os
import sys

# Add website directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'website'))

# Import the main app from website folder
from website.app import app as website_app

# Create a simple Flask app for the root
app = Flask(__name__)

@app.route('/')
def index():
    return redirect('/')

if __name__ == '__main__':
    # In production, this won't be used as gunicorn will run the app
    port = int(os.environ.get('PORT', 10000))
    website_app.run(host='0.0.0.0', port=port) 