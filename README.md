# YTC (YouTube Clone)

A comprehensive video sharing platform built with Django, featuring AI-powered recommendations, content moderation, and social features.

![YTC Screenshot](docs/images/screenshot.png)

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Database Setup](#-database-setup)
- [Running the Application](#-running-the-application)
- [Architecture](#-architecture)
- [API Documentation](#-api-documentation)
- [Project Structure](#-project-structure)
- [Recommendation System](#-recommendation-system)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)
- [Acknowledgements](#-acknowledgements)

## 🌟 Overview

YTC is a feature-rich video sharing platform inspired by YouTube, built using Django and modern web technologies. It includes AI-powered recommendations, BERT-based search, content moderation tools, and social features such as comments, likes, and user profiles.

## 🚀 Features

### Content Management
- Video upload and processing with FFmpeg
- Blog and post creation
- Category and tag organization
- Playlists with drag-and-drop sorting
- Customizable thumbnails

### User Experience
- Responsive design for all devices
- Personalized video feeds
- Real-time notifications
- Advanced search functionality
- User subscriptions and history tracking

### AI Features
- BERT-based semantic search
- Hybrid recommendation engine (collaborative and content-based)
- Automated content categorization
- View prediction and trending calculation

### Administration
- Content moderation dashboard
- User management tools
- Performance analytics
- Custom action logging

## 💻 Technology Stack

### Backend
- **Django 4.2.7**: Core web framework
- **PostgreSQL**: Primary database
- **Redis**: Caching and Celery broker
- **Celery**: Asynchronous task processing

### AI/ML
- **PyTorch**: Deep learning framework
- **Transformers**: NLP models
- **FAISS**: Similarity search
- **Scikit-learn**: Traditional ML algorithms

### Frontend
- **Bootstrap 5**: CSS framework
- **JavaScript/jQuery**: Frontend interactivity
- **HTMX**: AJAX functionality without JavaScript

### Infrastructure
- **Docker**: Containerization
- **Nginx**: Web server and reverse proxy
- **AWS S3/GCS**: Media storage (optional)

## 📝 Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.9 or higher
- PostgreSQL 13 or higher
- Redis 6 or higher
- FFmpeg 4.4+ (for video processing)
- Node.js 16+ (for frontend asset compilation, optional)
- Git

## 🔧 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/sohamdhobi/YouTube-Clone.git
cd ytc
```

### Step 2: Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt

# Optional: Install development dependencies
pip install -r requirements-dev.txt
```

### Step 4: Set Up Environment Variables

Create a `.env` file in the project root:

```
# Django
DEBUG=True
SECRET_KEY=your_secret_key_here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://your_username:your_password@localhost:5432/youtube_clone

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password

# Storage
MEDIA_ROOT=media/
STATIC_ROOT=staticfiles/

# AI Settings
COMPUTE_RECOMMENDATIONS=True
ENABLE_SEMANTIC_SEARCH=True

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
```

### Step 5: Install FFmpeg

#### Windows
1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract to a folder (e.g., C:\ffmpeg)
3. Add the bin folder to your PATH environment variable

#### macOS
```bash
brew install ffmpeg
```

#### Linux
```bash
sudo apt update
sudo apt install ffmpeg
```

Verify installation:
```bash 
ffmpeg -version
```

## ⚙️ Configuration

### Django Settings

Key settings to review in `settings.py`:

```python
# Django secret key - change for production
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')

# Debug mode - set to False in production
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Allowed hosts - modify for production
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# CSRF and CORS settings for production
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000').split(',')
```

### Email Configuration

```python
# Email settings - required for user verification
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
```

### Storage Configuration (for Production)

To use AWS S3 for media storage:

1. Install boto3: `pip install boto3 django-storages`
2. Add to settings.py:

```python
INSTALLED_APPS += ['storages']

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
AWS_S3_FILE_OVERWRITE = False

if os.environ.get('USE_S3', 'False') == 'True':
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

## 🗄️ Database Setup

### Create Database and User

```bash
# Log into PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE youtube_clone;

# Create user with password
CREATE USER ytc_user WITH PASSWORD 'secure_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE youtube_clone TO ytc_user;

# Exit PostgreSQL
\q
```

### Update Django Settings

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'youtube_clone',
        'USER': 'ytc_user',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Migrations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Seed Initial Data

```bash
# Load initial categories and tags
python manage.py loaddata initial_categories.json initial_tags.json

# Create test data (development only)
python manage.py create_test_data
```

## 💾 Database Backup and Integration

### Backup Database

1. **Create a backup**:
   ```bash
   # Windows
   pg_dump -U your_username youtube_clone > backup.sql

   # macOS/Linux
   pg_dump -U your_username youtube_clone > backup.sql
   ```

2. **Schedule automatic backups**:
   ```bash
   # Create a backup script (backup.sh)
   #!/bin/bash
   pg_dump -U your_username youtube_clone > /path/to/backups/backup_$(date +%Y%m%d).sql
   ```

3. **Restore from backup**:
   ```bash
   # Windows
   psql -U your_username youtube_clone < backup.sql

   # macOS/Linux
   psql -U your_username youtube_clone < backup.sql
   ```

### Database Integration

1. **Configure PostgreSQL**:
   ```bash
   # Install PostgreSQL
   # Windows: Download from https://www.postgresql.org/download/windows/
   # macOS: brew install postgresql
   # Linux: sudo apt install postgresql postgresql-contrib

   # Create database
   createdb youtube_clone

   # Create user
   createuser -P your_username
   ```

2. **Update Django settings**:
   ```python
   # settings.py
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'youtube_clone',
           'USER': 'your_username',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```

3. **Environment Variables**:
   Add to your `.env` file:
   ```
   DATABASE_URL=postgres://your_username:your_password@localhost:5432/youtube_clone
   ```

4. **Database Migrations**:
   ```bash
   # Create migrations
   python manage.py makemigrations

   # Apply migrations
   python manage.py migrate

   # Create superuser
   python manage.py createsuperuser
   ```

5. **Database Optimization**:
   ```bash
   # Create indexes for frequently queried fields
   python manage.py sqlmigrate core 0001_initial

   # Analyze database performance
   python manage.py dbshell
   \dt
   \d+ table_name
   ```

6. **Database Monitoring**:
   ```bash
   # Install pgAdmin for GUI monitoring
   # Or use command line tools:
   psql -U your_username youtube_clone
   \l  # List databases
   \dt # List tables
   \d+ table_name # Show table structure
   ```

### Backup Automation

1. **Using cron jobs (Linux/macOS)**:
   ```bash
   # Edit crontab
   crontab -e

   # Add daily backup at 2 AM
   0 2 * * * /path/to/backup.sh
   ```

2. **Using Windows Task Scheduler**:
   - Create a new task
   - Set trigger to daily at 2 AM
   - Action: Run backup script
   - Configure appropriate permissions

3. **Cloud Backup Integration**:
   ```bash
   # Example using AWS S3
   aws s3 cp backup.sql s3://your-bucket/backups/
   ```

## 🏃 Running the Application

### Development Server

```bash
# Start the Django development server
python manage.py runserver

# Access the site at http://127.0.0.1:8000
```

### Celery Worker (for background tasks)

```bash
# Start Redis (if not running)
redis-server

# Start Celery worker
celery -A youtube_clone worker -l info

# Start Celery beat for scheduled tasks
celery -A youtube_clone beat -l info
```

### Process Videos

```bash
# Process pending videos
python manage.py process_videos

# Generate embeddings for recommendation system
python manage.py generate_embeddings

# Precompute recommendations (run daily)
python manage.py precompute_recommendations
```

### Production Deployment

For production, use Gunicorn and Nginx:

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn youtube_clone.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

Nginx configuration example:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /path/to/youtube_clone;
    }

    location /media/ {
        root /path/to/youtube_clone;
    }

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

## 🏗️ Architecture

### Key Components

1. **Core Module**
   - Content management
   - Social features (likes, comments)
   - Feed generation
   - Reporting system

2. **Videos Module**
   - Video upload and processing
   - Player functionality
   - View tracking
   - Playlist management

3. **Users Module**
   - User authentication
   - Profile management
   - Subscription system
   - History tracking

4. **Notifications Module**
   - Real-time notifications
   - Email notifications
   - In-app notifications

5. **Recommendation Engine**
   - Content-based filtering
   - Collaborative filtering
   - Multi-armed bandit algorithm
   - A/B testing framework

### Data Flow

1. **Video Upload Process**
   - User uploads video
   - Celery processes video (transcoding, thumbnail generation)
   - Embeddings generated for recommendations
   - Video made available for viewing

2. **Recommendation Process**
   - User interactions tracked
   - Embeddings updated
   - Recommendations precomputed nightly
   - Personalized feed generated

3. **Search Process**
   - Query analyzed using BERT
   - Semantic matching with video embeddings
   - Results ranked by relevance
   - Filters applied (date, duration, etc.)

## 📚 API Documentation

### Authentication

```bash
# Get auth token
POST /api/token/
{
  "username": "your_username",
  "password": "your_password"
}

# Response
{
  "access": "your-access-token",
  "refresh": "your-refresh-token"
}
```

### Videos

```bash
# List videos
GET /api/videos/

# Get video detail
GET /api/videos/{id}/

# Upload video
POST /api/videos/
Content-Type: multipart/form-data
{
  "title": "Video Title",
  "description": "Video Description",
  "file": [binary data],
  "category": 1
}
```

### Users

```bash
# Get user profile
GET /api/users/{id}/

# Update profile
PATCH /api/users/{id}/
{
  "bio": "New bio",
  "avatar": [binary data]
}
```

## 📊 Database Schema

Key models in the system:

- `CustomUser`: Extended user model with profile fields
- `Video`: Core content model for videos, photos, and blogs
- `Playlist`, `PlaylistItem`: Playlist management
- `Comment`, `Like`: User interactions
- `VideoEmbedding`, `UserEmbedding`: AI features
- `BanditStats`: Recommendation engine data
- `Report`, `AdminLog`: Moderation system

## 📁 Project Structure

```
youtube_clone/
├── core/                   # Core functionality
│   ├── management/         # Custom management commands
│   ├── models.py           # Core data models
│   ├── recommender.py      # Recommendation engine
│   ├── search.py           # Search functionality
│   └── views.py            # Core views
├── videos/                 # Video-specific functionality
│   ├── models.py           # Video models
│   ├── processors.py       # Video processing
│   └── views.py            # Video views
├── users/                  # User management
│   ├── models.py           # User models
│   └── views.py            # User views
├── notifications/          # Notification system
│   ├── models.py           # Notification models
│   └── views.py            # Notification views
├── custom_admin/           # Admin interface
│   ├── models.py           # Admin models
│   └── views.py            # Admin views
├── static/                 # Static files
│   ├── css/                # Stylesheets
│   ├── js/                 # JavaScript
│   └── img/                # Images
├── templates/              # HTML templates
│   ├── core/               # Core templates
│   ├── videos/             # Video templates
│   └── users/              # User templates
├── media/                  # User-uploaded content
│   ├── videos/             # Uploaded videos
│   ├── thumbnails/         # Video thumbnails
│   └── avatars/            # User avatars
├── config/                 # Configuration
│   ├── settings.py         # Django settings
│   ├── urls.py             # URL routing
│   └── wsgi.py             # WSGI configuration
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## 🧠 Recommendation System

The recommendation system uses a hybrid approach:

1. **Content-Based Filtering**
   - Video transcripts and metadata analyzed
   - BERT embeddings generated for semantic understanding
   - Similar content recommended based on viewing history

2. **Collaborative Filtering**
   - User behavior analyzed (views, likes, watch time)
   - Matrix factorization used to find patterns
   - Item-item and user-user similarity calculated

3. **Multi-Armed Bandit**
   - Exploration vs. exploitation balance
   - A/B testing for algorithm improvement
   - Dynamic adjustment based on user feedback

To precompute recommendations:

```bash
# Run daily to update recommendations
python manage.py precompute_recommendations
```

## ❓ Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check PostgreSQL service is running
   - Verify database credentials in `.env`
   - Ensure database exists: `psql -l`

2. **FFmpeg Errors**
   - Verify FFmpeg installation: `ffmpeg -version`
   - Check PATH environment variable
   - Install required codecs: `sudo apt install ubuntu-restricted-extras`

3. **Celery Worker Not Starting**
   - Check Redis is running: `redis-cli ping`
   - Verify Celery configuration
   - Run with DEBUG=True for detailed logs

4. **Static Files Not Loading**
   - Run `python manage.py collectstatic`
   - Check STATIC_URL and STATIC_ROOT settings
   - Verify web server configuration

5. **Email Verification Issues**
   - Check email settings in `.env`
   - For Gmail, use App Password
   - Test email backend: `python manage.py sendtestemail your@email.com`

### Logs

Check logs for detailed error information:

```bash
# Django logs
cat logs/django.log

# Celery worker logs
cat logs/celery.log

# Nginx logs
cat /var/log/nginx/error.log
```

## 👥 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

### Coding Standards

- Follow PEP 8 for Python code
- Use Django's coding style for templates
- Add docstrings for all functions and classes
- Write tests for new features

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific tests
python manage.py test core.tests.TestRecommendationSystem

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- [Django](https://www.djangoproject.com/) - The web framework used
- [PostgreSQL](https://www.postgresql.org/) - Database backend
- [Bootstrap](https://getbootstrap.com/) - Frontend framework
- [FFmpeg](https://ffmpeg.org/) - Video processing
- [PyTorch](https://pytorch.org/) - Deep learning framework
- [Transformers](https://huggingface.co/transformers/) - NLP models
- [FAISS](https://github.com/facebookresearch/faiss) - Similarity search
- And all other open-source libraries used in this project 
