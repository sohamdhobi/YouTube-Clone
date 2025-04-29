from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count, Case, When, Value, IntegerField
from videos.models import Video, VideoView
from .models import Category, Tag, Post, Blog, Comment, Like, Report
from .forms import PostForm, BlogForm, CommentForm, ReportForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from notifications.models import Notification
from core.recommender import recommend_videos
import logging
from .bert_utils import semantic_search
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

def home(request):
    # Get the requested feed type (default to 'for_you')
    feed_type = request.GET.get('feed', 'for_you')
    
    # Load videos based on feed type
    if feed_type == 'trending':
        # Show all trending videos, no limit
        videos = Video.objects.filter(is_published=True).order_by('-views')
        is_personalized = False
    elif feed_type == 'latest':
        # Show all latest videos, no limit
        videos = Video.objects.filter(is_published=True).order_by('-created_at')
        is_personalized = False
    else:  # 'for_you' or default
        # Get recommended videos based on user interests
        if request.user.is_authenticated:
            # Personalized recommendations for authenticated users
            try:
                # Get all videos, no limit
                videos = recommend_videos(user_id=request.user.id, num_recommendations=9999)
                is_personalized = True
            except Exception as e:
                logger.error(f"Error generating personalized recommendations: {e}")
                # If recommendation engine fails, try to get videos from user's viewed categories
                try:
                    # Find categories from videos the user has watched
                    user_views = VideoView.objects.filter(user=request.user).values_list('video', flat=True)
                    watched_categories = Video.objects.filter(id__in=user_views).values_list('categories', flat=True).distinct()
                    
                    # Get videos from those categories, excluding ones already watched
                    videos = Video.objects.filter(
                        categories__in=watched_categories, 
                        is_published=True
                    ).exclude(
                        id__in=user_views
                    ).order_by('?')
                    
                    if not videos.exists():
                        # If still no videos, get newest videos
                        videos = Video.objects.filter(is_published=True).order_by('-created_at')
                        is_personalized = False
                    else:
                        is_personalized = True
                except Exception as inner_e:
                    logger.error(f"Error finding category-based recommendations: {inner_e}")
                    # Last resort - get newest videos
                    videos = Video.objects.filter(is_published=True).order_by('-created_at')
                    is_personalized = False
        else:
            # For anonymous users, use the recommendation engine without user_id
            videos = recommend_videos(user_id=None, num_recommendations=9999)
            # Mark as not personalized since it's based on general popularity
            is_personalized = False
    
    # Get user interest topics
    user_interest_topics = []
    if request.user.is_authenticated:
        # Get user's view history
        user_views = VideoView.objects.filter(user=request.user)
        
        if user_views.exists():
            # Get videos the user has watched
            watched_video_ids = user_views.values_list('video', flat=True)
            
            # Get categories from watched videos
            user_interest_topics = Category.objects.filter(
                videos__in=watched_video_ids
            ).annotate(
                view_count=Count('videos')
            ).order_by('-view_count')[:8]
        
        # If no interest topics found, get trending categories
        if not user_interest_topics:
            user_interest_topics = Category.objects.annotate(
                videos_count=Count('videos')
            ).order_by('-videos_count')[:8]
    else:
        # For anonymous users, just get trending categories
        user_interest_topics = Category.objects.annotate(
            videos_count=Count('videos')
        ).order_by('-videos_count')[:8]
    
    # Get trending topics (tags with most videos or views)
    trending_topics = Tag.objects.annotate(
        videos_count=Count('videos')
    ).order_by('-videos_count')[:8]
    
    # Get recommended channels
    recommended_channels = []
    if request.user.is_authenticated:
        # First try to get channels the user has watched but not subscribed to
        User = get_user_model()
        
        # Get creators of videos the user has watched
        if 'user_views' not in locals():
            user_views = VideoView.objects.filter(user=request.user)
            watched_video_ids = user_views.values_list('video', flat=True)
        
        # Get creators of videos the user has watched
        watched_creators = User.objects.filter(
            videos__in=watched_video_ids
        ).distinct()
        
        # Exclude creators the user is already subscribed to
        subscribed_creators = request.user.subscribed_to.all()
        recommended_channels_qs = watched_creators.exclude(
            id__in=subscribed_creators.values_list('id', flat=True)
        ).annotate(
            videos_count=Count('videos')
        ).order_by('-videos_count')[:5]
        
        # Convert to list of dicts with video count
        recommended_channels = []
        for channel in recommended_channels_qs:
            recommended_channels.append({
                'user': channel,
                'video_count': channel.videos_count
            })
        
        # Add some of the user's subscribed channels if recommendations aren't enough
        if len(recommended_channels) < 5 and subscribed_creators.exists():
            # Get the most active subscribed channels based on recent uploads
            active_subscriptions = subscribed_creators.annotate(
                videos_count=Count('videos')
            ).order_by('-videos_count')[:5-len(recommended_channels)]
            
            # Add to recommended channels list as dicts
            for channel in active_subscriptions:
                recommended_channels.append({
                    'user': channel,
                    'video_count': channel.videos_count
                })
    
    # If still no recommendations or not authenticated, get popular creators
    if not recommended_channels:
        User = get_user_model()
        
        # Get creators with the most views
        popular_creators = User.objects.filter(
            videos__isnull=False  # Only creators with videos
        ).annotate(
            videos_count=Count('videos'),
            view_count=Count('videos__video_views')
        ).order_by('-view_count')[:5]
        
        # Convert to list of dicts with video count
        for channel in popular_creators:
            recommended_channels.append({
                'user': channel,
                'video_count': channel.videos_count
            })
    
    return render(request, 'core/home.html', {
        'videos': videos,
        'user_interest_topics': user_interest_topics,
        'trending_topics': trending_topics,
        'recommended_channels': recommended_channels,
        'is_personalized': is_personalized,
        'feed_type': feed_type
    })

def category_list(request):
    categories = Category.objects.all()
    return render(request, 'core/category_list.html', {'categories': categories})

def category_detail(request, slug):
    category = Category.objects.get(slug=slug)
    videos = category.videos.filter(is_published=True)
    return render(request, 'core/category_detail.html', {
        'category': category,
        'videos': videos
    })

def search(request):
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'relevance')
    search_method = request.GET.get('method', 'semantic')  # 'semantic' for BERT, 'traditional' for DB
    
    if not query:
        return render(request, 'core/search.html', {'videos': [], 'query': query})
    
    # For semantic search using BERT embeddings
    if search_method == 'semantic':
        # Perform semantic search across all content types
        combined_results = []
        
        try:
            # Get semantic search results (returns tuples of (content_object, similarity_score))
            semantic_results = semantic_search(
                query, 
                content_types=[Video, Blog, Post],
                limit=100  # Get more results to allow for sorting
            )
            
            # Process the semantic results into the same format as traditional search
            for content_object, similarity_score in semantic_results:
                if isinstance(content_object, Video):
                    combined_results.append({
                        'type': 'video',
                        'object': content_object,
                        'title': content_object.title,
                        'description': content_object.description,
                        'creator': content_object.creator,
                        'created_at': content_object.created_at,
                        'views': content_object.views,
                        'thumbnail': content_object.thumbnail,
                        'slug': content_object.slug,
                        'content_type': 'video',
                        'duration': content_object.duration if hasattr(content_object, 'duration') else None,
                        'similarity': similarity_score,
                    })
                elif isinstance(content_object, Blog):
                    combined_results.append({
                        'type': 'blog',
                        'object': content_object,
                        'title': content_object.title,
                        'description': content_object.content[:200],
                        'creator': content_object.creator,
                        'created_at': content_object.created_at,
                        'views': content_object.likes.count(),
                        'thumbnail': content_object.image if hasattr(content_object, 'image') and content_object.image else None,
                        'slug': content_object.slug,
                        'content_type': 'blog',
                        'duration': None,
                        'similarity': similarity_score,
                    })
                elif isinstance(content_object, Post):
                    combined_results.append({
                        'type': 'post',
                        'object': content_object,
                        'title': content_object.content[:50] + '...' if len(content_object.content) > 50 else content_object.content,
                        'description': content_object.content[:200],
                        'creator': content_object.creator,
                        'created_at': content_object.created_at,
                        'views': content_object.likes.count(),
                        'thumbnail': content_object.image if hasattr(content_object, 'image') and content_object.image else None,
                        'slug': content_object.id,
                        'content_type': 'post',
                        'duration': None,
                        'similarity': similarity_score,
                    })
            
            # If semantic search returns no results, fall back to traditional search
            if not combined_results:
                search_method = 'traditional'
            else:
                # Apply sorting
                if sort_by == 'date':
                    combined_results.sort(key=lambda x: x['created_at'], reverse=True)
                elif sort_by == 'views':
                    combined_results.sort(key=lambda x: x['views'], reverse=True)
                # For 'relevance', we keep the semantic similarity score order
        
        except Exception as e:
            # Log the error
            logger.error(f"Error in semantic search: {e}")
            
            # Fall back to traditional search
            search_method = 'traditional'
    
    # Fall back to traditional DB search if requested or if semantic search failed
    if search_method == 'traditional':
        # Start with a base queryset that includes all videos
        videos = Video.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(creator__username__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct()
        
        # Also get blogs and posts that match the query
        blogs = Blog.objects.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query) | 
            Q(creator__username__icontains=query)
        ).distinct()
        
        posts = Post.objects.filter(
            Q(content__icontains=query) | 
            Q(creator__username__icontains=query)
        ).distinct()
        
        # Apply sorting
        if sort_by == 'date':
            videos = videos.order_by('-created_at')
            blogs = blogs.order_by('-created_at')
            posts = posts.order_by('-created_at')
        elif sort_by == 'views':
            videos = videos.order_by('-views')
            blogs = blogs.order_by('-likes')
            posts = posts.order_by('-likes')
        else:  # relevance - default
            # For relevance sorting, we prioritize exact matches and title matches
            # We use annotate to add a relevance score
            videos = videos.annotate(
                relevance=Case(
                    # Exact title match gets highest score
                    When(title__iexact=query, then=Value(5)),
                    # Title contains query gets high score
                    When(title__icontains=query, then=Value(4)),
                    # Creator username exact match
                    When(creator__username__iexact=query, then=Value(3)),
                    # Creator username contains
                    When(creator__username__icontains=query, then=Value(2)),
                    # Description contains
                    When(description__icontains=query, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ).order_by('-relevance', '-views', '-created_at')
            
            blogs = blogs.annotate(
                relevance=Case(
                    When(title__iexact=query, then=Value(5)),
                    When(title__icontains=query, then=Value(4)),
                    When(creator__username__iexact=query, then=Value(3)),
                    When(creator__username__icontains=query, then=Value(2)),
                    When(content__icontains=query, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ).order_by('-relevance', '-likes', '-created_at')
            
            posts = posts.annotate(
                relevance=Case(
                    When(creator__username__iexact=query, then=Value(3)),
                    When(creator__username__icontains=query, then=Value(2)),
                    When(content__icontains=query, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ).order_by('-relevance', '-likes', '-created_at')
        
        # Combine the results
        # First, let's prepare a common structure for all content types
        combined_results = []
        
        for video in videos:
            combined_results.append({
                'type': 'video',
                'object': video,
                'title': video.title,
                'description': video.description,
                'creator': video.creator,
                'created_at': video.created_at,
                'views': video.views,
                'thumbnail': video.thumbnail,
                'slug': video.slug,
                'content_type': 'video',
                'duration': video.duration if hasattr(video, 'duration') else None,
            })
        
        for blog in blogs:
            combined_results.append({
                'type': 'blog',
                'object': blog,
                'title': blog.title,
                'description': blog.content[:200],
                'creator': blog.creator,
                'created_at': blog.created_at,
                'views': blog.likes.count(),
                'thumbnail': blog.image if hasattr(blog, 'image') and blog.image else None,
                'slug': blog.slug,
                'content_type': 'blog',
                'duration': None,
            })
        
        for post in posts:
            combined_results.append({
                'type': 'post',
                'object': post,
                'title': post.content[:50] + '...' if len(post.content) > 50 else post.content,
                'description': post.content[:200],
                'creator': post.creator,
                'created_at': post.created_at,
                'views': post.likes.count(),
                'thumbnail': post.image if hasattr(post, 'image') and post.image else None,
                'slug': post.id,  # Posts might not have slugs, using ID instead
                'content_type': 'post',
                'duration': None,
            })
        
        # Final sorting based on the requested method
        if sort_by == 'date':
            combined_results.sort(key=lambda x: x['created_at'], reverse=True)
        elif sort_by == 'views':
            combined_results.sort(key=lambda x: x['views'], reverse=True)
        # For relevance, we rely on the database-level sorting we did earlier
    
    return render(request, 'core/search.html', {
        'videos': combined_results,
        'query': query,
        'sort': sort_by,
        'search_method': search_method
    })

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.creator = request.user
            post.save()
            return redirect('core:post_detail', slug=post.slug)
    else:
        form = PostForm()
    return render(request, 'core/post_form.html', {'form': form})

def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug)
    comments = post.comments.filter(parent=None)
    comment_form = CommentForm()
    
    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.user = request.user
            comment.post = post
            parent_id = request.POST.get('parent_id')
            if parent_id:
                comment.parent = get_object_or_404(Comment, id=parent_id)
            comment.save()
            return redirect('core:post_detail', slug=slug)
    
    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'is_liked': request.user.is_authenticated and post.likes.filter(id=request.user.id).exists()
    }
    return render(request, 'core/post_detail.html', context)

@login_required
def create_blog(request):
    if request.method == 'POST':
        form = BlogForm(request.POST)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.creator = request.user
            blog.save()
            return redirect('core:blog_detail', slug=blog.slug)
    else:
        form = BlogForm()
    return render(request, 'core/blog_form.html', {'form': form})

def blog_detail(request, slug):
    blog = get_object_or_404(Blog, slug=slug)
    comments = blog.comments.filter(parent=None)
    comment_form = CommentForm()
    
    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.user = request.user
            comment.blog = blog
            parent_id = request.POST.get('parent_id')
            if parent_id:
                comment.parent = get_object_or_404(Comment, id=parent_id)
            comment.save()
            return redirect('core:blog_detail', slug=slug)
    
    context = {
        'blog': blog,
        'comments': comments,
        'comment_form': comment_form,
        'is_liked': request.user.is_authenticated and blog.likes.filter(id=request.user.id).exists()
    }
    return render(request, 'core/blog_detail.html', context)

@login_required
@require_POST
def like_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    like, created = Like.objects.get_or_create(user=request.user, content_type=ContentType.objects.get_for_model(post), object_id=post.id)
    
    if created:
        create_notification(request.user, post.user, 'like', post)
        return JsonResponse({'status': 'liked'})
    else:
        like.delete()
        return JsonResponse({'status': 'unliked'})

@login_required
@require_POST
def like_blog(request, slug):
    blog = get_object_or_404(Blog, slug=slug)
    like, created = Like.objects.get_or_create(user=request.user, blog=blog)
    
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    
    return JsonResponse({
        'success': True,
        'liked': liked,
        'like_count': blog.like_count
    })

@login_required
@require_POST
def like_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    like, created = Like.objects.get_or_create(user=request.user, comment=comment)
    
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    
    return JsonResponse({
        'success': True,
        'liked': liked,
        'like_count': comment.like_count
    })

@login_required
def comment_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        text = request.POST.get('text')
        parent_id = request.POST.get('parent_id')
        
        if parent_id:
            parent_comment = get_object_or_404(Comment, id=parent_id)
            comment = Comment.objects.create(
                user=request.user,
                text=text,
                content_type=ContentType.objects.get_for_model(post),
                object_id=post.id,
                parent=parent_comment
            )
            create_notification(request.user, parent_comment.user, 'reply', comment)
        else:
            comment = Comment.objects.create(
                user=request.user,
                text=text,
                content_type=ContentType.objects.get_for_model(post),
                object_id=post.id
            )
            create_notification(request.user, post.user, 'comment', comment)
        
        return redirect('core:post_detail', pk=pk)
    return redirect('core:post_detail', pk=pk)

@login_required
def subscribed_channels(request):
    # Get all channels the user is subscribed to
    subscribed_channels = request.user.subscribed_to.all()
    
    # Get latest videos from subscribed channels
    latest_videos = Video.objects.filter(
        creator__in=subscribed_channels,
        is_published=True
    ).order_by('-created_at')[:30]  # Increased from 20 to 30 videos
    
    # Get latest posts from subscribed channels
    latest_posts = Post.objects.filter(
        creator__in=subscribed_channels
    ).order_by('-created_at')[:10]
    
    # Get latest blogs from subscribed channels
    latest_blogs = Blog.objects.filter(
        creator__in=subscribed_channels
    ).order_by('-created_at')[:10]
    
    return render(request, 'core/subscribed_channels.html', {
        'subscribed_channels': subscribed_channels,
        'latest_videos': latest_videos,
        'latest_posts': latest_posts,
        'latest_blogs': latest_blogs
    })

@login_required
def latest_videos(request):
    # Get all latest videos from all channels
    latest_videos = Video.objects.filter(
        is_published=True
    ).order_by('-created_at')[:20]
    
    return render(request, 'core/latest_videos.html', {
        'latest_videos': latest_videos
    })

@login_required
def report_content(request, content_type, object_id):
    """View for reporting content (videos, images, blogs, etc.)"""
    from django.contrib.contenttypes.models import ContentType
    from .forms import ReportForm
    from .models import Report
    from videos.models import Video
    
    # Get the content type and object
    try:
        # Map the URL content type string to the actual ContentType model
        content_type_map = {
            'video': ContentType.objects.get_for_model(Video),
            'photo': ContentType.objects.get_for_model(Video),  # Photos are in the Video model
            'blog': ContentType.objects.get_for_model(Video),   # Blogs are in the Video model
            'comment': ContentType.objects.get_for_model(Comment),
        }
        
        if content_type not in content_type_map:
            return redirect('core:home')
            
        ct = content_type_map[content_type]
        
        # Try to get the object
        obj = ct.get_object_for_this_type(id=object_id)
        
        # Get the content title for the confirmation message
        if hasattr(obj, 'title'):
            content_title = obj.title
        elif hasattr(obj, 'content'):
            # For comments, show a preview
            content_title = obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
        else:
            content_title = f"{content_type} #{object_id}"
            
        # Check if the user has already reported this content
        existing_report = Report.objects.filter(
            content_type=ct,
            object_id=object_id,
            reporter=request.user,
            status__in=['pending', 'reviewed']
        ).exists()
        
        if existing_report:
            messages.info(request, "You've already reported this content. Our team is reviewing it.")
            
            # Redirect back to the content
            if content_type in ['video', 'photo', 'blog'] and hasattr(obj, 'slug'):
                return redirect('videos:watch', slug=obj.slug)
            return redirect('core:home')
            
        if request.method == 'POST':
            form = ReportForm(request.POST)
            if form.is_valid():
                report = form.save(commit=False)
                report.content_type = ct
                report.object_id = object_id
                report.reporter = request.user
                report.save()
                
                # Send notification to moderators
                from django.contrib.auth import get_user_model
                
                User = get_user_model()
                # Find moderator admins (level 2)
                moderators = User.objects.filter(is_admin=True, admin_role__level=2)
                
                # Notify all moderators
                for moderator in moderators:
                    # Create a notification using the Notification model directly
                    Notification.objects.create(
                        sender=request.user,
                        recipient=moderator,
                        notification_type='report',
                        content_type=ContentType.objects.get_for_model(obj),
                        object_id=obj.id,
                        verb=f"New report from {request.user.username}",
                        description=f"Report reason: {form.cleaned_data.get('reason')}",
                        url=f"/custom-admin/content/{obj.id}/"
                    )
                
                messages.success(request, f"Thank you for reporting this {content_type}. Our team will review it promptly.")
                
                # Redirect back to the content
                if content_type in ['video', 'photo', 'blog'] and hasattr(obj, 'slug'):
                    return redirect('videos:watch', slug=obj.slug)
                return redirect('core:home')
        else:
            form = ReportForm()
        
        return render(request, 'core/report_content.html', {
            'form': form,
            'content_type': content_type,
            'content_title': content_title,
            'object': obj
        })
        
    except (ContentType.DoesNotExist, AttributeError) as e:
        print(f"Error in report_content: {str(e)}")
        messages.error(request, "There was an error processing your report. Please try again.")
        return redirect('core:home')
