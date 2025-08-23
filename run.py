#!/usr/bin/env python3
"""
Development server runner for the Flask blog backend.
"""

import os
import sys
from app import app

if __name__ == '__main__':
    # Ensure we're in the correct directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  Warning: .env file not found!")
        print("   Copy .env.example to .env and configure your settings.")
        print("   Example: cp .env.example .env")
        
    # Run the Flask development server
    print("🚀 Starting Flask development server...")
    print("   Server: http://localhost:5000")
    print("   Health check: http://localhost:5000/api/health")
    print("   Press Ctrl+C to stop")
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        use_reloader=True
    )
