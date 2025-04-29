import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from django.conf import settings
from videos.models import Video
from core.models import VideoEmbedding, UserEmbedding
import logging
from django.core.cache import cache
from django.db.models import Q
import time

# Set up logging
logger = logging.getLogger(__name__)

# Constants
EMBEDDING_DIMENSION = 768  # BERT base embedding dimension
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # Smaller, faster model that works well for similarity
CACHE_TTL = 60 * 60 * 24  # 24 hours in seconds

# Singleton pattern for model and tokenizer to avoid loading multiple times
class BERTSingleton:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize the BERT model and tokenizer"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            self.model = AutoModel.from_pretrained(MODEL_NAME)
            # Set model to evaluation mode
            self.model.eval()
            logger.info(f"BERT model {MODEL_NAME} loaded successfully")
        except Exception as e:
            logger.error(f"Error loading BERT model: {e}")
            self.tokenizer = None
            self.model = None

# Functions for generating and retrieving embeddings
def get_bert_embedding(text):
    """
    Generate a BERT embedding for a text string.
    
    Args:
        text (str): Text to generate embedding for
        
    Returns:
        numpy.ndarray: Embedding vector or None if failed
    """
    if not text:
        return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    
    # Get model instance
    bert = BERTSingleton.get_instance()
    if bert.model is None or bert.tokenizer is None:
        logger.error("BERT model not initialized")
        return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    
    try:
        # Tokenize and get embeddings
        with torch.no_grad():
            inputs = bert.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            outputs = bert.model(**inputs)
            
            # Use the [CLS] token embedding as the sentence embedding
            embedding = outputs.last_hidden_state[:, 0, :].numpy().flatten()
            
            return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)

def generate_video_embedding(video):
    """
    Generate embedding for a video by combining title, description, and tags.
    
    Args:
        video (Video): Video object
        
    Returns:
        numpy.ndarray: Combined embedding vector
    """
    # Combine metadata with appropriate weighting
    metadata = []
    
    # Title is most important (weight: 3)
    if video.title:
        metadata.extend([video.title] * 3)
    
    # Description is next (weight: 2)
    if video.description:
        metadata.extend([video.description] * 2)
    
    # Tags (weight: 1)
    try:
        # Assuming tags are stored as a related model or in a field
        if hasattr(video, 'tags'):
            tags = ' '.join([tag.name for tag in video.tags.all()])
            if tags:
                metadata.append(tags)
    except:
        pass
    
    # Categories (weight: 1)
    try:
        if hasattr(video, 'categories'):
            categories = ' '.join([cat.name for cat in video.categories.all()])
            if categories:
                metadata.append(categories)
    except:
        pass
    
    # Combine all metadata
    combined_text = ' '.join(metadata)
    
    # Get embedding
    return get_bert_embedding(combined_text)

def calculate_user_preference_embedding(user):
    """
    Calculate a user's preference embedding based on their interactions
    
    Args:
        user (CustomUser): User object
        
    Returns:
        numpy.ndarray: User preference embedding
    """
    from django.db.models import Count, F, Sum
    
    # Get videos the user has interacted with, ordered by interaction strength
    # Combine likes, comments, and views with different weights
    videos = Video.objects.filter(
        Q(likes__user=user) |  # User liked the video
        Q(comments__user=user) |  # User commented on the video
        Q(video_views__user=user)  # User viewed the video
    ).annotate(
        interaction_score=Count('likes', filter=Q(likes__user=user)) * 5 +  # Likes have high weight
                      Count('comments', filter=Q(comments__user=user)) * 3 +  # Comments have medium weight
                      Sum(F('video_views__view_time'), filter=Q(video_views__user=user)) / 60  # View time in minutes
    ).order_by('-interaction_score')[:20]  # Limit to top 20 videos
    
    if not videos:
        # If user has no interactions, return zero vector
        return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    
    # Get embeddings for these videos
    embeddings = []
    
    for video in videos:
        # Try to get from database first
        try:
            video_embedding = VideoEmbedding.objects.get(video=video)
            embedding = video_embedding.get_vector()
            embeddings.append(embedding * (video.interaction_score / 10.0))  # Weight by interaction score
        except VideoEmbedding.DoesNotExist:
            # Generate embedding if not in database
            embedding = generate_video_embedding(video)
            # Store for future use
            VideoEmbedding.create_from_video(video, embedding)
            embeddings.append(embedding * (video.interaction_score / 10.0))
    
    if not embeddings:
        return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    
    # Average the embeddings
    user_embedding = np.mean(embeddings, axis=0)
    
    # Normalize the embedding
    norm = np.linalg.norm(user_embedding)
    if norm > 0:
        user_embedding = user_embedding / norm
    
    return user_embedding

def get_or_create_video_embedding(video_id):
    """
    Get a video's embedding from cache or database, or create if doesn't exist
    
    Args:
        video_id (int): ID of the video
        
    Returns:
        numpy.ndarray: Video embedding
    """
    # Try cache first
    cache_key = f"video_embedding_{video_id}"
    cached_embedding = cache.get(cache_key)
    
    if cached_embedding is not None:
        return cached_embedding
    
    # Try database
    try:
        video = Video.objects.get(id=video_id)
        try:
            embedding_obj = VideoEmbedding.objects.get(video=video)
            embedding = embedding_obj.get_vector()
            
            # Store in cache
            cache.set(cache_key, embedding, CACHE_TTL)
            
            return embedding
        except VideoEmbedding.DoesNotExist:
            # Generate new embedding
            embedding = generate_video_embedding(video)
            
            # Store in database
            VideoEmbedding.create_from_video(video, embedding)
            
            # Store in cache
            cache.set(cache_key, embedding, CACHE_TTL)
            
            return embedding
    except Video.DoesNotExist:
        return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)

def get_or_create_user_embedding(user_id):
    """
    Get a user's preference embedding from cache or database, or create if doesn't exist
    
    Args:
        user_id (int): ID of the user
        
    Returns:
        numpy.ndarray: User preference embedding
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Try cache first
    cache_key = f"user_embedding_{user_id}"
    cached_embedding = cache.get(cache_key)
    
    if cached_embedding is not None:
        return cached_embedding
    
    # Try database
    try:
        user = User.objects.get(id=user_id)
        
        try:
            embedding_obj = UserEmbedding.objects.get(user=user)
            # Check if it's recent enough (less than 24 hours old)
            from django.utils import timezone
            if timezone.now() - embedding_obj.updated_at < timezone.timedelta(days=1):
                embedding = embedding_obj.get_vector()
                
                # Store in cache
                cache.set(cache_key, embedding, CACHE_TTL)
                
                return embedding
        except UserEmbedding.DoesNotExist:
            pass
        
        # Generate new embedding
        embedding = calculate_user_preference_embedding(user)
        
        # Store in database
        UserEmbedding.create_from_user(user, embedding)
        
        # Store in cache
        cache.set(cache_key, embedding, CACHE_TTL)
        
        return embedding
    except User.DoesNotExist:
        return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)

def calculate_similarity(embedding1, embedding2):
    """
    Calculate cosine similarity between two embeddings
    
    Args:
        embedding1 (numpy.ndarray): First embedding
        embedding2 (numpy.ndarray): Second embedding
        
    Returns:
        float: Cosine similarity (-1 to 1, higher is more similar)
    """
    if embedding1 is None or embedding2 is None:
        return 0.0
    
    # Check for zero vectors
    if np.all(embedding1 == 0) or np.all(embedding2 == 0):
        return 0.0
    
    # Calculate cosine similarity
    similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
    return float(similarity)

def batch_generate_embeddings(max_videos=1000):
    """
    Generate embeddings for videos that don't have them yet
    
    Args:
        max_videos (int): Maximum number of videos to process
        
    Returns:
        int: Number of embeddings generated
    """
    # Get videos without embeddings
    videos_without_embeddings = Video.objects.filter(
        ~Q(embedding__isnull=False)
    ).order_by('-created_at')[:max_videos]
    
    count = 0
    start_time = time.time()
    
    for video in videos_without_embeddings:
        embedding = generate_video_embedding(video)
        VideoEmbedding.create_from_video(video, embedding)
        count += 1
        
        # Log progress
        if count % 100 == 0:
            elapsed = time.time() - start_time
            logger.info(f"Generated {count} embeddings in {elapsed:.2f} seconds")
    
    elapsed = time.time() - start_time
    logger.info(f"Finished generating {count} embeddings in {elapsed:.2f} seconds")
    
    return count 