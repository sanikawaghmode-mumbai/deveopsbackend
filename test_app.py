import pytest
import json
import os
import tempfile
from app import app, db
from config import TestingConfig

@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    app.config.from_object(TestingConfig)
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

@pytest.fixture
def admin_headers():
    """Headers with admin authentication."""
    return {
        'Authorization': f'Bearer {os.getenv("ADMIN_TOKEN", "test-admin-token")}',
        'Content-Type': 'application/json'
    }

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_get_posts_empty(client):
    """Test getting posts when none exist."""
    response = client.get('/api/posts')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == []

def test_create_post(client, admin_headers):
    """Test creating a new post."""
    post_data = {
        'title': 'Test Post',
        'content': 'This is a test post content.',
        'image_url': 'https://example.com/image.jpg'
    }
    
    response = client.post('/api/posts', 
                          data=json.dumps(post_data),
                          headers=admin_headers)
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == post_data['title']
    assert data['content'] == post_data['content']
    assert data['image_url'] == post_data['image_url']
    assert 'id' in data
    assert 'created_at' in data

def test_create_post_without_auth(client):
    """Test creating a post without admin authentication."""
    post_data = {
        'title': 'Test Post',
        'content': 'This is a test post content.'
    }
    
    response = client.post('/api/posts', 
                          data=json.dumps(post_data),
                          headers={'Content-Type': 'application/json'})
    
    assert response.status_code == 401

def test_get_posts_with_data(client, admin_headers):
    """Test getting posts when data exists."""
    # Create a post first
    post_data = {
        'title': 'Test Post',
        'content': 'This is a test post content.'
    }
    
    client.post('/api/posts', 
                data=json.dumps(post_data),
                headers=admin_headers)
    
    # Get all posts
    response = client.get('/api/posts')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['title'] == post_data['title']

def test_get_specific_post(client, admin_headers):
    """Test getting a specific post."""
    # Create a post first
    post_data = {
        'title': 'Specific Test Post',
        'content': 'This is a specific test post content.'
    }
    
    create_response = client.post('/api/posts', 
                                 data=json.dumps(post_data),
                                 headers=admin_headers)
    
    created_post = json.loads(create_response.data)
    post_id = created_post['id']
    
    # Get the specific post
    response = client.get(f'/api/posts/{post_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == post_data['title']
    assert data['id'] == post_id

def test_update_post(client, admin_headers):
    """Test updating a post."""
    # Create a post first
    post_data = {
        'title': 'Original Title',
        'content': 'Original content.'
    }
    
    create_response = client.post('/api/posts', 
                                 data=json.dumps(post_data),
                                 headers=admin_headers)
    
    created_post = json.loads(create_response.data)
    post_id = created_post['id']
    
    # Update the post
    update_data = {
        'title': 'Updated Title',
        'content': 'Updated content.'
    }
    
    response = client.put(f'/api/posts/{post_id}',
                         data=json.dumps(update_data),
                         headers=admin_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == update_data['title']
    assert data['content'] == update_data['content']

def test_delete_post(client, admin_headers):
    """Test deleting a post."""
    # Create a post first
    post_data = {
        'title': 'Post to Delete',
        'content': 'This post will be deleted.'
    }
    
    create_response = client.post('/api/posts', 
                                 data=json.dumps(post_data),
                                 headers=admin_headers)
    
    created_post = json.loads(create_response.data)
    post_id = created_post['id']
    
    # Delete the post
    response = client.delete(f'/api/posts/{post_id}', headers=admin_headers)
    assert response.status_code == 200
    
    # Verify it's deleted
    get_response = client.get(f'/api/posts/{post_id}')
    assert get_response.status_code == 404

def test_newsletter_signup(client):
    """Test newsletter subscription."""
    email_data = {
        'email': 'test@example.com'
    }
    
    response = client.post('/api/newsletter/signup',
                          data=json.dumps(email_data),
                          headers={'Content-Type': 'application/json'})
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'Successfully subscribed' in data['message']

def test_newsletter_signup_duplicate(client):
    """Test newsletter subscription with duplicate email."""
    email_data = {
        'email': 'duplicate@example.com'
    }
    
    # First subscription
    client.post('/api/newsletter/signup',
                data=json.dumps(email_data),
                headers={'Content-Type': 'application/json'})
    
    # Second subscription (duplicate)
    response = client.post('/api/newsletter/signup',
                          data=json.dumps(email_data),
                          headers={'Content-Type': 'application/json'})
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'already subscribed' in data['message']

def test_get_subscribers(client, admin_headers):
    """Test getting all newsletter subscribers."""
    # Add a subscriber first
    email_data = {
        'email': 'subscriber@example.com'
    }
    
    client.post('/api/newsletter/signup',
                data=json.dumps(email_data),
                headers={'Content-Type': 'application/json'})
    
    # Get subscribers
    response = client.get('/api/newsletter/subscribers', headers=admin_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['email'] == email_data['email']

def test_get_nonexistent_post(client):
    """Test getting a post that doesn't exist."""
    response = client.get('/api/posts/999')
    assert response.status_code == 404

if __name__ == '__main__':
    pytest.main([__file__])
