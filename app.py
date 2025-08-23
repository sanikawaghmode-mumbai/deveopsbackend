import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///blog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db = SQLAlchemy(app)
CORS(app, origins=['http://localhost:5173'])

# AWS S3 Configuration
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)
S3_BUCKET = os.getenv('S3_BUCKET_NAME')

# Models
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat()
        }

class NewsletterSubscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'subscribed_at': self.subscribed_at.isoformat()
        }

# Utility functions
def upload_to_s3(file, bucket_name, object_name=None):
    """Upload a file to an S3 bucket"""
    if object_name is None:
        object_name = file.filename

    try:
        s3_client.upload_fileobj(
            file, 
            bucket_name, 
            object_name,
            ExtraArgs={'ContentType': file.content_type}
        )
        return f"https://{bucket_name}.s3.amazonaws.com/{object_name}"
    except ClientError as e:
        return None

def send_newsletter_email(to_email, subject, content):
    """Send newsletter email"""
    try:
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        sender_email = os.getenv('SENDER_EMAIL')
        sender_password = os.getenv('SENDER_PASSWORD')

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(content, 'html'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email to {to_email}: {str(e)}")
        return False

# Routes



@app.route('/api/posts', methods=['GET'])
def get_posts():
    """Get all posts"""
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return jsonify([post.to_dict() for post in posts])

@app.route('/api/posts', methods=['POST'])
def create_post():
    """Create a new post"""
    data = request.get_json()
    
    if not data or not data.get('title') or not data.get('content'):
        return jsonify({'error': 'Title and content are required'}), 400
    
    post = Post(
        title=data['title'],
        content=data['content'],
        image_url=data.get('image_url')
    )
    
    db.session.add(post)
    db.session.commit()
    
    return jsonify(post.to_dict()), 201

@app.route('/api/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Get a specific post"""
    post = Post.query.get_or_404(post_id)
    return jsonify(post.to_dict())

@app.route('/api/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    """Update a specific post"""
    post = Post.query.get_or_404(post_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    post.title = data.get('title', post.title)
    post.content = data.get('content', post.content)
    post.image_url = data.get('image_url', post.image_url)
    
    db.session.commit()
    return jsonify(post.to_dict())

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    """Delete a specific post"""
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': 'Post deleted successfully'})

@app.route('/api/upload', methods=['POST'])
def upload_image():
    """Upload image to S3 and return public URL"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        url = upload_to_s3(file, S3_BUCKET, filename)
        if url:
            return jsonify({'url': url})
        else:
            return jsonify({'error': 'Failed to upload file'}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/newsletter/signup', methods=['POST'])
def newsletter_signup():
    """Subscribe to newsletter"""
    data = request.get_json()
    
    if not data or not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
    
    email = data['email'].lower().strip()
    
    # Check if already subscribed
    existing_subscriber = NewsletterSubscriber.query.filter_by(email=email).first()
    if existing_subscriber:
        return jsonify({'message': 'Email already subscribed'}), 200
    
    subscriber = NewsletterSubscriber(email=email)
    db.session.add(subscriber)
    db.session.commit()
    
    return jsonify({'message': 'Successfully subscribed to newsletter'}), 201

@app.route('/api/newsletter/send', methods=['POST'])
def send_newsletter():
    """Send newsletter to all subscribers"""
    data = request.get_json()
    
    if not data or not data.get('subject') or not data.get('content'):
        return jsonify({'error': 'Subject and content are required'}), 400
    
    subscribers = NewsletterSubscriber.query.all()
    if not subscribers:
        return jsonify({'message': 'No subscribers found'}), 200
    
    success_count = 0
    failed_count = 0
    
    for subscriber in subscribers:
        if send_newsletter_email(subscriber.email, data['subject'], data['content']):
            success_count += 1
        else:
            failed_count += 1
    
    return jsonify({
        'message': f'Newsletter sent successfully',
        'success_count': success_count,
        'failed_count': failed_count,
        'total_subscribers': len(subscribers)
    })

@app.route('/api/newsletter/subscribers', methods=['GET'])
def get_subscribers():
    """Get all newsletter subscribers"""
    subscribers = NewsletterSubscriber.query.order_by(NewsletterSubscriber.subscribed_at.desc()).all()
    return jsonify([subscriber.to_dict() for subscriber in subscribers])

@app.route('/api/newsletter/unsubscribe/<int:subscriber_id>', methods=['DELETE'])
def unsubscribe(subscriber_id):
    """Remove a subscriber"""
    subscriber = NewsletterSubscriber.query.get_or_404(subscriber_id)
    db.session.delete(subscriber)
    db.session.commit()
    return jsonify({'message': 'Subscriber removed successfully'})

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# Initialize database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
