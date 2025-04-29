import numpy as np
from django.db.models import F, Q, Count, Avg, Sum, Case, When, Value, FloatField
from django.core.cache import cache
from videos.models import Video, VideoView
from core.models import BanditStats, VideoEmbedding, UserEmbedding, Like
from core.nlp import get_or_create_video_embedding, get_or_create_user_embedding, calculate_similarity
import logging
import random
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from functools import lru_cache

# Set up logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_NUM_RECOMMENDATIONS = 100  # Increased to show more videos by default
MAX_RECOMMENDATIONS = 1000  # Maximum number of videos to fetch
CACHE_TTL = 60 * 10  # 10 minutes in seconds
POPULARITY_WEIGHT = 0.3  # Weight given to popularity versus similarity
NOVELTY_WEIGHT = 0.2  # Weight for novelty (recency)
EXPLORATION_RATE = 0.1  # Probability of exploring random videos
WATCH_TIME_WEIGHT = 0.4  # Weight for user watch time patterns
LIKE_WEIGHT = 0.5  # Weight for liked content (strong signal)
COLLAB_WEIGHT = 0.3  # Weight for collaborative filtering

class ContextualBanditRecommender:
    """
    Implements a Contextual Bandit algorithm for video recommendations.
    Uses a hybrid approach combining content-based similarity and collaborative filtering signals.
    """
    
    def __init__(self, exploration_rate=EXPLORATION_RATE):
        """
        Initialize the recommender
        
        Args:
            exploration_rate (float): Probability of exploring random videos (0-1)
        """
        self.exploration_rate = exploration_rate
    
    def recommend_for_user(self, user_id, num_recommendations=DEFAULT_NUM_RECOMMENDATIONS, exclude_watched=True):
        """
        Generate recommendations for a user
        
        Args:
            user_id (int): ID of the user
            num_recommendations (int): Number of videos to recommend
            exclude_watched (bool): Whether to exclude videos the user has already watched
            
        Returns:
            list: List of Video objects
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Try cache first for frequent users
        cache_key = f"user_recommendations_{user_id}_{num_recommendations}_{exclude_watched}"
        cached_recs = cache.get(cache_key)
        
        if cached_recs is not None:
            try:
                # Convert cached video IDs back to Video objects
                videos = Video.objects.filter(id__in=cached_recs)
                if len(videos) == len(cached_recs):
                    return videos
            except:
                pass  # If there's any issue, just regenerate recommendations
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            # If user doesn't exist, return popular videos
            return self.get_popular_videos(num_recommendations)
            
        # Decide if we should explore or exploit
        if random.random() < self.exploration_rate:
            # Exploration: Get some random recent videos
            return self.get_exploration_videos(user, num_recommendations, exclude_watched)
        else:
            # Exploitation: Get personalized recommendations using our hybrid approach
            
            # 1. Content-based recommendations
            content_based_videos = self.get_personalized_videos(user, num_recommendations * 2, exclude_watched)
            
            # 2. Collaborative filtering recommendations
            collaborative_videos = self.get_collaborative_recommendations(user, num_recommendations, exclude_watched)
            
            # 3. Videos from categories user has watched most
            category_videos = self.get_category_recommendations(user, num_recommendations, exclude_watched)
            
            # 4. Videos similar to what user has liked
            liked_content_videos = self.get_recommendations_from_likes(user, num_recommendations, exclude_watched)
            
            # 5. Videos user has watched longest (for similar content)
            watch_time_videos = self.get_watch_time_recommendations(user, num_recommendations, exclude_watched)
            
            # Combine all recommendation sources with weights
            # Remove duplicates while preserving order of importance
            all_videos = []
            video_ids_seen = set()
            
            # Liked content is highest priority (strongest signal)
            for video in liked_content_videos:
                if video.id not in video_ids_seen:
                    all_videos.append(video)
                    video_ids_seen.add(video.id)
            
            # Videos user has watched longest (strong signal of interest)  
            for video in watch_time_videos:
                if video.id not in video_ids_seen:
                    all_videos.append(video)
                    video_ids_seen.add(video.id)
            
            # Content-based recommendations
            for video in content_based_videos:
                if video.id not in video_ids_seen:
                    all_videos.append(video)
                    video_ids_seen.add(video.id)
            
            # Collaborative filtering recommendations
            for video in collaborative_videos:
                if video.id not in video_ids_seen:
                    all_videos.append(video)
                    video_ids_seen.add(video.id)
            
            # Category-based recommendations
            for video in category_videos:
                if video.id not in video_ids_seen:
                    all_videos.append(video)
                    video_ids_seen.add(video.id)
            
            # If we don't have enough videos, supplement with popular ones
            if len(all_videos) < num_recommendations:
                popular_videos = self.get_popular_videos(num_recommendations - len(all_videos))
                for video in popular_videos:
                    if video.id not in video_ids_seen:
                        all_videos.append(video)
                        video_ids_seen.add(video.id)
            
            # Apply UCB ranking to select final videos
            ranked_videos = self.rank_videos_ucb(user, all_videos)[:num_recommendations]
            
            # Cache the recommendations
            cache.set(cache_key, [video.id for video in ranked_videos], CACHE_TTL)
            
            return ranked_videos
    
    def get_personalized_videos(self, user, num_videos, exclude_watched=True):
        """
        Get personalized video recommendations for a user based on content similarity
        
        Args:
            user (User): User object
            num_videos (int): Number of videos to recommend
            exclude_watched (bool): Whether to exclude videos the user has already watched
            
        Returns:
            list: List of Video objects
        """
        # Get user embedding
        user_embedding = get_or_create_user_embedding(user.id)
        
        # Get candidate videos
        # Start with recent videos that match the user's preferred categories/tags if available
        candidate_videos = Video.objects.filter(
            is_published=True,
            moderation_status='approved'
        )
        
        # Exclude watched videos if requested
        if exclude_watched:
            watched_video_ids = Video.objects.filter(
                video_views__user=user
            ).values_list('id', flat=True)
            candidate_videos = candidate_videos.exclude(id__in=watched_video_ids)
            
        # Prioritize videos from subscribed channels
        subscribed_creator_ids = user.subscribed_to.values_list('id', flat=True)
        
        # Mix of subscribed and general content
        if subscribed_creator_ids:
            # Get videos from subscribed channels
            subscribed_videos = candidate_videos.filter(
                creator_id__in=subscribed_creator_ids
            ).order_by('-created_at')
            
            # Get videos from general content
            other_videos = candidate_videos.exclude(
                creator_id__in=subscribed_creator_ids
            ).order_by('-created_at')
            
            # Combine both sets but prioritize subscribed content
            candidate_videos = list(subscribed_videos) + list(other_videos)
        else:
            # If no subscriptions, just get recent videos
            candidate_videos = candidate_videos.order_by('-created_at')
        
        # Get video embeddings and calculate similarity scores
        video_similarities = []
        
        for video in candidate_videos:
            try:
                video_embedding = get_or_create_video_embedding(video.id)
                similarity = calculate_similarity(user_embedding, video_embedding)
                
                # Adjust with popularity and recency boosts
                try:
                    # Popularity factor (0 to 1 scale based on views)
                    popularity = min(1.0, video.views / 10000)
                    
                    # Recency factor (1.0 for new, decreasing with age)
                    days_old = (timezone.now() - video.created_at).days
                    recency = max(0.1, 1.0 - (days_old / 30))  # Linear decay over 30 days, minimum 0.1
                    
                    # Final score combining similarity, popularity, and recency
                    score = (
                        similarity * (1 - POPULARITY_WEIGHT - NOVELTY_WEIGHT) + 
                        popularity * POPULARITY_WEIGHT + 
                        recency * NOVELTY_WEIGHT
                    )
                except:
                    # If any error calculating adjustments, just use similarity
                    score = similarity
                
                video_similarities.append((video, score))
            except:
                # If any error with embeddings, just add with low score
                video_similarities.append((video, 0.1))
        
        # Sort by similarity score
        video_similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Extract just the videos
        return [video for video, _ in video_similarities[:num_videos]]
    
    def get_recommendations_from_likes(self, user, num_videos, exclude_watched=True):
        """
        Get recommendations based on videos similar to what the user has liked
        
        Args:
            user (User): User object
            num_videos (int): Number of videos to recommend
            exclude_watched (bool): Whether to exclude videos the user has already watched
            
        Returns:
            list: List of Video objects
        """
        # Get content types for videos
        video_content_type = ContentType.objects.get_for_model(Video)
        
        # Get videos the user has liked
        liked_videos = Video.objects.filter(
            likes__user=user
        )
        
        if not liked_videos.exists():
            return []
        
        # Get candidate videos
        candidate_videos = Video.objects.filter(
            is_published=True,
            moderation_status='approved'
        )
        
        # Exclude watched videos if requested
        if exclude_watched:
            watched_video_ids = Video.objects.filter(
                video_views__user=user
            ).values_list('id', flat=True)
            candidate_videos = candidate_videos.exclude(id__in=watched_video_ids)
        
        # Also exclude already liked videos
        candidate_videos = candidate_videos.exclude(
            id__in=liked_videos.values_list('id', flat=True)
        )
        
        # Get embeddings for liked videos
        liked_embeddings = []
        for video in liked_videos:
            try:
                embedding = get_or_create_video_embedding(video.id)
                liked_embeddings.append(embedding)
            except:
                pass
        
        if not liked_embeddings:
            return []
        
        # Calculate similarity between candidate videos and liked videos
        similar_videos = []
        for candidate in candidate_videos:
            try:
                candidate_embedding = get_or_create_video_embedding(candidate.id)
                
                # Calculate average similarity to all liked videos
                total_similarity = sum(
                    calculate_similarity(candidate_embedding, liked_embedding)
                    for liked_embedding in liked_embeddings
                )
                avg_similarity = total_similarity / len(liked_embeddings)
                
                similar_videos.append((candidate, avg_similarity))
            except:
                pass
        
        # Sort by similarity score
        similar_videos.sort(key=lambda x: x[1], reverse=True)
        
        # Extract just the videos
        return [video for video, _ in similar_videos[:num_videos]]
    
    def get_collaborative_recommendations(self, user, num_videos, exclude_watched=True):
        """
        Get recommendations based on what similar users have watched
        
        Args:
            user (User): User object
            num_videos (int): Number of videos to recommend
            exclude_watched (bool): Whether to exclude videos the user has already watched
            
        Returns:
            list: List of Video objects
        """
        # Find users with similar viewing patterns
        watched_video_ids = VideoView.objects.filter(
            user=user
        ).values_list('video_id', flat=True).distinct()
        
        if not watched_video_ids:
            return []
        
        # Find users who watched at least 2 of the same videos
        similar_users = VideoView.objects.filter(
            video_id__in=watched_video_ids,
        ).exclude(
            user=user
        ).values('user').annotate(
            overlap=Count('user')
        ).filter(
            overlap__gte=2
        ).order_by('-overlap')[:20]  # Top 20 similar users
        
        if not similar_users:
            return []
        
        similar_user_ids = [u['user'] for u in similar_users]
        
        # Get videos that these similar users have watched but user hasn't
        collaborative_videos = Video.objects.filter(
            video_views__user_id__in=similar_user_ids,
            is_published=True,
            moderation_status='approved'
        )
        
        if exclude_watched:
            collaborative_videos = collaborative_videos.exclude(
                id__in=watched_video_ids
            )
        
        # Rank by popularity among similar users
        collaborative_videos = collaborative_videos.annotate(
            similar_user_views=Count(
                'video_views',
                filter=Q(video_views__user_id__in=similar_user_ids)
            )
        ).order_by('-similar_user_views')
        
        return list(collaborative_videos[:num_videos])
    
    def get_watch_time_recommendations(self, user, num_videos, exclude_watched=True):
        """
        Get recommendations based on videos that the user has watched for longest time
        
        Args:
            user (User): User object
            num_videos (int): Number of videos to recommend
            exclude_watched (bool): Whether to exclude videos the user has already watched
            
        Returns:
            list: List of Video objects
        """
        # Get the videos the user has watched the longest
        long_watch_videos = VideoView.objects.filter(
            user=user,
            view_time__gte=60  # At least 1 minute to be significant
        ).values('video').annotate(
            total_time=Sum('view_time')
        ).order_by('-total_time')[:10]  # Top 10 videos with longest watch time
        
        if not long_watch_videos:
            return []
        
        long_watch_video_ids = [v['video'] for v in long_watch_videos]
        
        # Get similar videos to those with long watch times
        similar_videos = []
        
        for video_id in long_watch_video_ids:
            try:
                # Get embedding for this long-watched video
                source_embedding = get_or_create_video_embedding(video_id)
                
                # Find similar videos
                candidate_videos = Video.objects.filter(
                    is_published=True,
                    moderation_status='approved'
                )
                
                if exclude_watched:
                    watched_ids = VideoView.objects.filter(
                        user=user
                    ).values_list('video_id', flat=True).distinct()
                    candidate_videos = candidate_videos.exclude(id__in=watched_ids)
                
                # Also exclude the source videos themselves
                candidate_videos = candidate_videos.exclude(id__in=long_watch_video_ids)
                
                # Look for similar videos
                for candidate in candidate_videos:
                    try:
                        candidate_embedding = get_or_create_video_embedding(candidate.id)
                        similarity = calculate_similarity(source_embedding, candidate_embedding)
                        similar_videos.append((candidate, similarity))
                    except:
                        pass
            except:
                pass
        
        # Remove duplicates and sort by similarity
        deduplicated = {}
        for video, score in similar_videos:
            if video.id not in deduplicated or score > deduplicated[video.id][1]:
                deduplicated[video.id] = (video, score)
        
        sorted_videos = sorted(deduplicated.values(), key=lambda x: x[1], reverse=True)
        
        # Extract just the videos
        return [video for video, _ in sorted_videos[:num_videos]]
    
    def get_category_recommendations(self, user, num_videos, exclude_watched=True):
        """
        Get recommendations based on the categories the user has watched most
        
        Args:
            user (User): User object
            num_videos (int): Number of videos to recommend
            exclude_watched (bool): Whether to exclude videos the user has already watched
            
        Returns:
            list: List of Video objects
        """
        # Find the most watched categories
        watched_video_ids = VideoView.objects.filter(
            user=user
        ).values_list('video_id', flat=True).distinct()
        
        if not watched_video_ids:
            return []
        
        from django.db.models import Count
        
        # Get categories from watched videos with count
        from core.models import Category
        most_watched_categories = Category.objects.filter(
            videos__in=watched_video_ids
        ).annotate(
            watch_count=Count('videos')
        ).order_by('-watch_count')[:5]  # Top 5 categories
        
        if not most_watched_categories:
            return []
        
        category_ids = [c.id for c in most_watched_categories]
        
        # Get videos from those categories
        category_videos = Video.objects.filter(
            categories__in=category_ids,
            is_published=True,
            moderation_status='approved'
        )
        
        if exclude_watched:
            category_videos = category_videos.exclude(id__in=watched_video_ids)
        
        # Rank by matching multiple top categories and then by views
        category_videos = category_videos.annotate(
            category_match_count=Count('categories', filter=Q(categories__in=category_ids)),
            relevance=F('category_match_count') * 10 + F('views') * 0.01
        ).order_by('-relevance')
        
        return list(category_videos[:num_videos])
    
    def get_popular_videos(self, num_videos):
        """
        Get popular videos for cold start and anonymous users
        
        Args:
            num_videos (int): Number of videos to return
            
        Returns:
            list: List of Video objects
        """
        # Try cache first
        cache_key = f"popular_videos_{num_videos}"
        cached_videos = cache.get(cache_key)
        
        if cached_videos is not None and num_videos <= MAX_RECOMMENDATIONS // 2:
            try:
                # Convert cached video IDs back to Video objects
                videos = Video.objects.filter(id__in=cached_videos)
                if len(videos) == num_videos:
                    return videos
            except:
                pass  # If there's any issue, just regenerate recommendations
        
        # Get trending videos based on views in the past week
        one_week_ago = timezone.now() - timedelta(days=7)
        
        videos = Video.objects.filter(
            is_published=True,
            moderation_status='approved',
            created_at__gte=one_week_ago
        ).annotate(
            recent_views=Count('video_views', filter=Q(video_views__created_at__gte=one_week_ago))
        ).order_by('-recent_views')
        
        # If we don't have enough recent videos, get all-time popular videos
        if len(videos) < num_videos:
            more_videos = Video.objects.filter(
                is_published=True,
                moderation_status='approved'
            ).exclude(
                id__in=[v.id for v in videos]
            ).order_by('-views')
            
            videos = list(videos) + list(more_videos)
        
        # Cache the results only if it's a reasonable size
        if num_videos <= MAX_RECOMMENDATIONS // 2:
            cache.set(cache_key, [video.id for video in videos[:num_videos]], CACHE_TTL)
        
        return videos[:num_videos]
    
    def get_exploration_videos(self, user, num_videos, exclude_watched=True):
        """
        Get random exploration videos for the user to discover new content
        
        Args:
            user (User): User object
            num_videos (int): Number of videos to return
            exclude_watched (bool): Whether to exclude videos the user has already watched
            
        Returns:
            list: List of Video objects
        """
        # Get candidate videos
        candidate_videos = Video.objects.filter(
            is_published=True,
            moderation_status='approved'
        )
        
        # Exclude watched videos if requested
        if exclude_watched:
            watched_video_ids = Video.objects.filter(
                video_views__user=user
            ).values_list('id', flat=True)
            candidate_videos = candidate_videos.exclude(id__in=watched_video_ids)
        
        # Prioritize recent videos
        recent_cutoff = timezone.now() - timedelta(days=30)
        recent_videos = candidate_videos.filter(
            created_at__gte=recent_cutoff
        ).order_by('?')
        
        # If we don't have enough recent videos, get some random ones
        if recent_videos.count() < num_videos:
            more_videos = candidate_videos.exclude(
                id__in=recent_videos.values_list('id', flat=True)
            ).order_by('?')
            
            # Combine lists but limit to requested number
            recent_list = list(recent_videos)
            more_list = list(more_videos)
            combined = recent_list + more_list
            return combined[:num_videos]
        else:
            return list(recent_videos[:num_videos])
    
    def rank_videos_ucb(self, user, videos):
        """
        Rank videos using Upper Confidence Bound algorithm
        
        Args:
            user (User): User object
            videos (list): List of Video objects
            
        Returns:
            list: Sorted list of Video objects
        """
        # Get bandit stats for each video
        video_stats = []
        
        for video in videos:
            # Get or create bandit stats
            stats, created = BanditStats.objects.get_or_create(video=video)
            
            if created:
                # New videos get high UCB to encourage exploration
                stats.ucb_score = float('inf')
            
            # Get user-video similarity as contextual information
            try:
                user_embedding = get_or_create_user_embedding(user.id)
                video_embedding = get_or_create_video_embedding(video.id)
                similarity = calculate_similarity(user_embedding, video_embedding)
            except:
                similarity = 0.0
            
            # Adjust UCB score based on similarity
            adjusted_score = stats.ucb_score * (1.0 + similarity)
            
            video_stats.append((video, adjusted_score))
        
        # Sort by adjusted UCB score
        video_stats.sort(key=lambda x: x[1], reverse=True)
        
        # Extract just the videos
        return [video for video, _ in video_stats]
    
    def update_stats(self, video_id, user_id, clicked=False, watch_time=0):
        """
        Update bandit statistics after a recommendation is shown or clicked
        
        Args:
            video_id (int): ID of the video
            user_id (int): ID of the user
            clicked (bool): Whether the video was clicked
            watch_time (int): Watch time in seconds (if clicked)
            
        Returns:
            bool: Success or failure
        """
        try:
            # Get bandit stats
            stats, created = BanditStats.objects.get_or_create(video_id=video_id)
            
            # Update stats
            stats.update_stats(clicked=clicked, watch_time=watch_time)
            
            return True
        except Exception as e:
            logger.error(f"Error updating bandit stats: {e}")
            return False

def recommend_videos(user_id=None, num_recommendations=DEFAULT_NUM_RECOMMENDATIONS):
    """
    Helper function to get video recommendations for a user or anonymous visitor
    
    Args:
        user_id (int): ID of the user, or None for anonymous
        num_recommendations (int): Number of videos to recommend
        
    Returns:
        list: List of Video objects
    """
    recommender = ContextualBanditRecommender()
    
    # If requesting a very large number or None, use our MAX_RECOMMENDATIONS constant
    if num_recommendations is None or num_recommendations > MAX_RECOMMENDATIONS:
        num_recommendations = MAX_RECOMMENDATIONS
    
    if user_id:
        return recommender.recommend_for_user(user_id, num_recommendations)
    else:
        return recommender.get_popular_videos(num_recommendations)

def precompute_recommendations():
    """
    Background task to precompute recommendations for active users
    Should be called periodically by a scheduler (e.g., Celery)
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Get active users (who have logged in recently)
    one_month_ago = timezone.now() - timedelta(days=30)
    active_users = User.objects.filter(
        last_login__gte=one_month_ago
    )
    
    recommender = ContextualBanditRecommender()
    
    # Precompute recommendations for each active user
    for user in active_users:
        try:
            # Generate recommendations
            recommendations = recommender.recommend_for_user(user.id, DEFAULT_NUM_RECOMMENDATIONS)
            
            # Cache the results
            cache_key = f"user_recommendations_{user.id}_{DEFAULT_NUM_RECOMMENDATIONS}_True"
            cache.set(cache_key, [video.id for video in recommendations], CACHE_TTL * 6)  # Longer TTL for precomputed
            
            logger.info(f"Precomputed recommendations for user {user.id}")
        except Exception as e:
            logger.error(f"Error precomputing recommendations for user {user.id}: {e}")
    
    # Also update popular videos cache
    try:
        popular_videos = recommender.get_popular_videos(DEFAULT_NUM_RECOMMENDATIONS)
        cache_key = f"popular_videos_{DEFAULT_NUM_RECOMMENDATIONS}"
        cache.set(cache_key, [video.id for video in popular_videos], CACHE_TTL * 6)
        logger.info("Precomputed popular videos")
    except Exception as e:
        logger.error(f"Error precomputing popular videos: {e}")
    
    return True 