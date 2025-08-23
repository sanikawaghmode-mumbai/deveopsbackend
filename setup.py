#!/usr/bin/env python3
"""
Setup script for the Flask blog backend.
"""

import os
import sys
import subprocess
import secrets
import string

def generate_secret_key(length=32):
    """Generate a secure secret key."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_env_file():
    """Create .env file from template with generated secrets."""
    if os.path.exists('.env'):
        print("📁 .env file already exists. Skipping creation.")
        return
    
    if not os.path.exists('.env.example'):
        print("❌ .env.example not found!")
        return
    
    # Read the template
    with open('.env.example', 'r') as f:
        template = f.read()
    
    # Replace placeholder values
    secret_key = generate_secret_key()
    admin_token = generate_secret_key(24)
    
    env_content = template.replace('your-secret-key-here', secret_key)
    env_content = env_content.replace('your-admin-token-here', admin_token)
    
    # Write the .env file
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env file with generated secrets")
    print(f"📝 Admin token: {admin_token}")
    print("⚠️  Remember to configure AWS S3 and email settings in .env")

def install_dependencies():
    """Install Python dependencies."""
    print("📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False
    return True

def initialize_database():
    """Initialize the SQLite database."""
    print("🗄️  Initializing database...")
    try:
        import app
        with app.app.app_context():
            app.db.create_all()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False
    return True

def main():
    """Main setup function."""
    print("🚀 Setting up Flask Blog Backend")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("❌ app.py not found. Make sure you're in the flask-be directory.")
        sys.exit(1)
    
    # Create .env file
    create_env_file()
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Configure AWS S3 settings in .env")
    print("2. Configure email settings in .env (for newsletter)")
    print("3. Run the server: python run.py")
    print("4. Test the API: curl http://localhost:5000/api/health")
    print("\n📖 See README.md for API documentation and examples")

if __name__ == '__main__':
    main()
