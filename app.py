"""
Alternative entry point: app.py
Some platforms expect this filename
Redirects to the main application
"""
from wsgi import app, application

# Expose both names for compatibility
__all__ = ['app', 'application']
