"""
WSGI entry point for production deployment
Compatible with Gunicorn, uWSGI, etc.
"""
import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

# Import Flask app
from src.api.main import app

# Expose app for WSGI servers
# For Gunicorn: gunicorn wsgi:app
# For uWSGI: uwsgi --http :8080 --wsgi-file wsgi.py --callable app
application = app

if __name__ == "__main__":
    # Fallback for direct execution
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
