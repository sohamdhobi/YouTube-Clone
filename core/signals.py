from django.db.models.signals import post_save
from django.dispatch import receiver
from videos.models import Video
from .models import Blog, Post
from .bert_utils import create_or_update_content_embedding
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Video)
def create_video_embedding(sender, instance, created, **kwargs):
    """Create or update embedding when video is saved"""
    if instance.is_published:  # Only create embeddings for published videos
        try:
            create_or_update_content_embedding(instance)
            logger.info(f"Created/updated embedding for Video: {instance.id}")
        except Exception as e:
            logger.error(f"Error creating embedding for Video {instance.id}: {str(e)}")

@receiver(post_save, sender=Blog)
def create_blog_embedding(sender, instance, created, **kwargs):
    """Create or update embedding when blog is saved"""
    try:
        create_or_update_content_embedding(instance)
        logger.info(f"Created/updated embedding for Blog: {instance.id}")
    except Exception as e:
        logger.error(f"Error creating embedding for Blog {instance.id}: {str(e)}")

@receiver(post_save, sender=Post)
def create_post_embedding(sender, instance, created, **kwargs):
    """Create or update embedding when post is saved"""
    try:
        create_or_update_content_embedding(instance)
        logger.info(f"Created/updated embedding for Post: {instance.id}")
    except Exception as e:
        logger.error(f"Error creating embedding for Post {instance.id}: {str(e)}") 