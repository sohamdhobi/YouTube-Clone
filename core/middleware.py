import re
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from core.recommender import ContextualBanditRecommender
import logging

logger = logging.getLogger(__name__)

class RecommendationTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track video recommendations and update Contextual Bandit statistics.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.video_pattern = re.compile(r'^/videos/(\d+)/')
        self.recommender = ContextualBanditRecommender()
    
    def process_request(self, request):
        """Process each request to track video interactions"""
        # Only process if user is authenticated
        if not request.user.is_authenticated:
            return None
        
        # Check if this is a video view request
        path = request.path
        match = self.video_pattern.match(path)
        
        if match:
            video_id = int(match.group(1))
            user_id = request.user.id
            
            # Get watch time if provided (from AJAX calls)
            watch_time = 0
            if request.method == 'POST' and 'watch_time' in request.POST:
                try:
                    watch_time = int(request.POST.get('watch_time', 0))
                except ValueError:
                    watch_time = 0
            
            # Update bandit stats for clicked recommendation
            try:
                # Check if this was a recommended video
                if 'rec_source' in request.GET:
                    self.recommender.update_stats(
                        video_id=video_id,
                        user_id=user_id,
                        clicked=True,
                        watch_time=watch_time
                    )
                    
                    # Store recommendation source in session for tracking
                    if 'rec_sources' not in request.session:
                        request.session['rec_sources'] = {}
                    
                    request.session['rec_sources'][str(video_id)] = {
                        'source': request.GET.get('rec_source'),
                        'clicked_at': timezone.now().isoformat()
                    }
                    request.session.modified = True
            except Exception as e:
                logger.error(f"Error tracking recommendation click: {e}")
        
        return None
    
    def process_response(self, request, response):
        """Process response to add tracking parameters to recommendations"""
        # Return unchanged response for non-HTML responses
        content_type = response.get('Content-Type', '')
        if 'text/html' not in content_type or not hasattr(response, 'content'):
            return response
        
        # Add tracking parameters to recommendation links if this is the home page
        if request.path == '/' and hasattr(response, 'content'):
            try:
                content = response.content.decode('utf-8')
                
                # Find recommendation links and add tracking parameter
                pattern = r'href=["\'](/videos/\d+/[^"\']*)["\']'
                
                def add_tracking(match):
                    link = match.group(1)
                    separator = '&' if '?' in link else '?'
                    return f'href="{link}{separator}rec_source=home"'
                
                modified_content = re.sub(pattern, add_tracking, content)
                
                # Update response content
                response.content = modified_content.encode('utf-8')
            except Exception as e:
                logger.error(f"Error adding tracking to recommendations: {e}")
        
        return response 