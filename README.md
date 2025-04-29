## 📊 Database Schema

Key models in the system:

- `CustomUser`: Extended user model with profile fields
- `Video`: Core content model for videos, photos, and blogs
- `Playlist`, `PlaylistItem`: Playlist management
- `Comment`, `Like`: User interactions
- `VideoEmbedding`, `UserEmbedding`: AI features
- `BanditStats`: Recommendation engine data
- `Report`, `AdminLog`: Moderation system

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
