from django.core.management.base import BaseCommand
from videos.models import Video
from core.models import Blog, Post
from core.bert_utils import create_or_update_content_embedding
from django.db import transaction
import time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate BERT embeddings for all content in the database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--content-type',
            choices=['video', 'blog', 'post', 'all'],
            default='all',
            help='Type of content to generate embeddings for'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of items to process per batch'
        )
    
    def handle(self, *args, **options):
        content_type = options['content_type']
        batch_size = options['batch_size']
        
        self.stdout.write(f"Generating embeddings for content type: {content_type}")
        
        stats = {
            'video': {'total': 0, 'success': 0, 'failed': 0},
            'blog': {'total': 0, 'success': 0, 'failed': 0},
            'post': {'total': 0, 'success': 0, 'failed': 0},
        }
        
        if content_type in ['video', 'all']:
            self._process_videos(batch_size, stats['video'])
        
        if content_type in ['blog', 'all']:
            self._process_blogs(batch_size, stats['blog'])
        
        if content_type in ['post', 'all']:
            self._process_posts(batch_size, stats['post'])
        
        # Print summary
        self.stdout.write(self.style.SUCCESS("\nEmbedding Generation Summary:"))
        for ctype, stat in stats.items():
            if stat['total'] > 0:
                self.stdout.write(f"{ctype.title()}s: {stat['success']}/{stat['total']} successful ({100 * stat['success'] / stat['total']:.1f}%)")
                if stat['failed'] > 0:
                    self.stdout.write(self.style.WARNING(f"  {stat['failed']} failed"))
        
        self.stdout.write(self.style.SUCCESS('Done!'))
    
    def _process_videos(self, batch_size, stats):
        """Process all videos in batches"""
        videos = Video.objects.filter(is_published=True).order_by('id')
        total = videos.count()
        stats['total'] = total
        
        if total == 0:
            self.stdout.write("No videos found.")
            return
        
        self.stdout.write(f"Processing {total} videos...")
        
        start_time = time.time()
        processed = 0
        
        for i in range(0, total, batch_size):
            batch = videos[i:i+batch_size]
            with transaction.atomic():
                for video in batch:
                    try:
                        create_or_update_content_embedding(video)
                        stats['success'] += 1
                    except Exception as e:
                        stats['failed'] += 1
                        logger.error(f"Error generating embedding for Video {video.id}: {str(e)}")
            
            processed += len(batch)
            elapsed = time.time() - start_time
            remaining = (elapsed / processed) * (total - processed) if processed > 0 else 0
            
            self.stdout.write(f"Progress: {processed}/{total} videos - {100 * processed / total:.1f}% - ETA: {remaining:.1f}s")
    
    def _process_blogs(self, batch_size, stats):
        """Process all blogs in batches"""
        blogs = Blog.objects.all().order_by('id')
        total = blogs.count()
        stats['total'] = total
        
        if total == 0:
            self.stdout.write("No blogs found.")
            return
        
        self.stdout.write(f"Processing {total} blogs...")
        
        start_time = time.time()
        processed = 0
        
        for i in range(0, total, batch_size):
            batch = blogs[i:i+batch_size]
            with transaction.atomic():
                for blog in batch:
                    try:
                        create_or_update_content_embedding(blog)
                        stats['success'] += 1
                    except Exception as e:
                        stats['failed'] += 1
                        logger.error(f"Error generating embedding for Blog {blog.id}: {str(e)}")
            
            processed += len(batch)
            elapsed = time.time() - start_time
            remaining = (elapsed / processed) * (total - processed) if processed > 0 else 0
            
            self.stdout.write(f"Progress: {processed}/{total} blogs - {100 * processed / total:.1f}% - ETA: {remaining:.1f}s")
    
    def _process_posts(self, batch_size, stats):
        """Process all posts in batches"""
        posts = Post.objects.all().order_by('id')
        total = posts.count()
        stats['total'] = total
        
        if total == 0:
            self.stdout.write("No posts found.")
            return
        
        self.stdout.write(f"Processing {total} posts...")
        
        start_time = time.time()
        processed = 0
        
        for i in range(0, total, batch_size):
            batch = posts[i:i+batch_size]
            with transaction.atomic():
                for post in batch:
                    try:
                        create_or_update_content_embedding(post)
                        stats['success'] += 1
                    except Exception as e:
                        stats['failed'] += 1
                        logger.error(f"Error generating embedding for Post {post.id}: {str(e)}")
            
            processed += len(batch)
            elapsed = time.time() - start_time
            remaining = (elapsed / processed) * (total - processed) if processed > 0 else 0
            
            self.stdout.write(f"Progress: {processed}/{total} posts - {100 * processed / total:.1f}% - ETA: {remaining:.1f}s") 