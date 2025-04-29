from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Video, Playlist, PlaylistItem, VideoView
from core.models import Comment, Like
from .forms import VideoForm, PlaylistForm
from core.forms import CommentForm
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from users.views import create_notification
import json
from django.core.exceptions import PermissionDenied
from .utils import convert_video_to_hls, check_ffmpeg
import os
from django.conf import settings
import uuid
from django.utils.text import slugify
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Sum

# Create your views here.

@login_required
def video_upload(request):
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.creator = request.user
            video.requires_moderation = True
            video.moderation_status = 'pending'
            
            # Use the is_published field from the form, but only set after moderation
            # Store this preference in moderation_notes for use by moderators
            publish_after_moderation = form.cleaned_data.get('is_published', True)
            video.is_published = False  # Always start unpublished until approved
            
            # Store the user's publication preference for moderators
            if publish_after_moderation:
                video.moderation_notes = "Publish after approval: Yes"
            else:
                video.moderation_notes = "Publish after approval: No"
            
            # Set default values to prevent NOT NULL constraint violations
            video.hls_url = ''
            video.is_processing = False
            
            # For photos and blogs, make sure the upload paths are set correctly
            if video.content_type == 'photo':
                if not video.image and 'image' in request.FILES:
                    video.image = request.FILES['image']
                # For photos, use the image itself as the thumbnail if no thumbnail provided
                if not video.thumbnail and video.image:
                    video.thumbnail = video.image
                    
            elif video.content_type == 'blog':
                # Make sure blog has a thumbnail
                if not video.thumbnail and 'thumbnail' in request.FILES:
                    video.thumbnail = request.FILES['thumbnail']
            
            # Save the model first to generate a slug and apply any other model logic
            video.save()
            
            # Only process videos, not photos or blog posts
            if video.content_type == 'video' and video.file:
                try:
                    # Mark video as processing
                    video.is_processing = True
                    video.save()
                    
                    # Get the path to the uploaded video file
                    video_path = os.path.join(settings.MEDIA_ROOT, video.file.name)
                    
                    # Check if ffmpeg is available
                    if check_ffmpeg():
                        # Convert the video to HLS format
                        success, result = convert_video_to_hls(video_path)
                        
                        if success:
                            # Update the video model with the HLS URL
                            video.hls_url = result
                            video.is_processing = False
                            video.save()
                            if publish_after_moderation:
                                messages.success(request, 'Video uploaded successfully! It will be reviewed by our moderation team before publishing.')
                            else:
                                messages.success(request, 'Video uploaded successfully! It will remain private after approval until you choose to publish it.')
                        else:
                            # Fallback to direct video URL if HLS conversion fails
                            video.hls_url = video.file.url  # Use the direct file URL as fallback
                            video.is_processing = False
                            video.save()
                            if publish_after_moderation:
                                messages.warning(request, f'Video uploaded but HLS conversion failed: {result}. Using direct video playback. Your content will be reviewed by our moderation team before publishing.')
                            else:
                                messages.warning(request, f'Video uploaded but HLS conversion failed: {result}. Using direct video playback. It will remain private after approval until you choose to publish it.')
                    else:
                        # FFmpeg not available - use direct file URL
                        video.hls_url = video.file.url
                        video.is_processing = False
                        video.save()
                        if publish_after_moderation:
                            messages.warning(request, 'Video uploaded but HLS conversion is not available. Using direct video playback. Your content will be reviewed by our moderation team before publishing.')
                        else:
                            messages.warning(request, 'Video uploaded but HLS conversion is not available. Using direct video playback. It will remain private after approval until you choose to publish it.')
                except Exception as e:
                    # General exception handling - use direct file URL
                    video.hls_url = video.file.url
                    video.is_processing = False
                    video.save()
                    if publish_after_moderation:
                        messages.warning(request, f'Video uploaded but processing encountered an error: {str(e)}. Using direct video playback. Your content will be reviewed by our moderation team before publishing.')
                    else:
                        messages.warning(request, f'Video uploaded but processing encountered an error: {str(e)}. Using direct video playback. It will remain private after approval until you choose to publish it.')
            else:
                # For photos and blogs, set appropriate success messages
                if video.content_type == 'photo':
                    if publish_after_moderation:
                        messages.success(request, 'Photo uploaded successfully! It will be reviewed by our moderation team before publishing.')
                    else:
                        messages.success(request, 'Photo uploaded successfully! It will remain private after approval until you choose to publish it.')
                elif video.content_type == 'blog':
                    if publish_after_moderation:
                        messages.success(request, 'Blog post created successfully! It will be reviewed by our moderation team before publishing.')
                    else:
                        messages.success(request, 'Blog post created successfully! It will remain private after approval until you choose to publish it.')
                else:
                    if publish_after_moderation:
                        messages.success(request, 'Content uploaded successfully! It will be reviewed by our moderation team before publishing.')
                    else:
                        messages.success(request, 'Content uploaded successfully! It will remain private after approval until you choose to publish it.')
                
            # Check for errors in saving the model    
            print(f"DEBUG - Uploaded content ID: {video.id}, Type: {video.content_type}")
            if video.content_type == 'photo':
                print(f"DEBUG - Photo image path: {video.image.name if video.image else 'None'}")
            elif video.content_type == 'blog':
                print(f"DEBUG - Blog thumbnail path: {video.thumbnail.name if video.thumbnail else 'None'}")
                
            return redirect('videos:watch', slug=video.slug)
    else:
        form = VideoForm()
    return render(request, 'videos/upload.html', {'form': form})

def video_detail(request, slug):
    # Get the video without checking published status initially
    video = get_object_or_404(Video, slug=slug)
    
    # Check if the user is allowed to view this video
    if not video.is_published:
        # Only allow creator or admin to view unpublished videos
        if not request.user.is_authenticated or (request.user != video.creator and not request.user.is_admin):
            messages.error(request, "This content is not available.")
            return redirect('core:home')
    
    comments = video.comments.filter(parent=None)
    is_liked = request.user.is_authenticated and Like.objects.filter(video=video, user=request.user).exists()
    is_subscribed = request.user.is_authenticated and video.creator.subscribers.filter(id=request.user.id).exists()
    
    # Add like status to comments
    if request.user.is_authenticated:
        for comment in comments:
            comment.is_liked_by_user = Like.objects.filter(comment=comment, user=request.user).exists()
            for reply in comment.replies.all():
                reply.is_liked_by_user = Like.objects.filter(comment=reply, user=request.user).exists()
        
    # Record view using the enhanced VideoView model
    is_recommendation = 'rec_source' in request.GET
    
    # Only record view if: 
    # - content is published OR
    # - viewed by someone other than the creator
    if video.is_published or (request.user.is_authenticated and request.user != video.creator):
        # Get client info
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        referrer = request.META.get('HTTP_REFERER', '')
        
        # Determine device type based on user agent (simple version)
        device = 'mobile' if 'Mobile' in user_agent else 'desktop'
        
        # Record view with initial zero watch time
        # Watch time will be updated via AJAX later
        VideoView.record_view(
            video=video,
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key,
            ip_address=ip_address,
            view_time=0,  # Initial view, will be updated via AJAX
            referrer=referrer,
            device=device,
            is_recommendation=is_recommendation
        )
        
        # Update recommendation stats if this was a recommendation
        if is_recommendation and request.user.is_authenticated:
            try:
                from core.recommender import ContextualBanditRecommender
                recommender = ContextualBanditRecommender()
                recommender.update_stats(
                    video_id=video.id,
                    user_id=request.user.id,
                    clicked=True,
                    watch_time=0  # Initial click, will be updated
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error updating recommendation stats: {e}")
        
        # Refresh the video from database to get updated view count
        video.refresh_from_db()
    
    # Get related videos using recommendation engine
    if request.user.is_authenticated:
        try:
            from core.recommender import recommend_videos
            related_videos = recommend_videos(user_id=request.user.id, num_recommendations=6)
        except Exception:
            # Fallback to simple related videos
            related_videos = Video.objects.filter(
                is_published=True,
                moderation_status='approved'
            ).exclude(id=video.id).order_by('-created_at')[:6]
    else:
        # For anonymous users, just show similar videos by category/tags
        try:
            # Try to get videos with similar tags or categories
            if hasattr(video, 'tags') and video.tags.exists():
                tags = video.tags.all()
                related_videos = Video.objects.filter(
                    tags__in=tags,
                    is_published=True
                ).exclude(id=video.id).distinct()[:6]
            elif hasattr(video, 'categories') and video.categories.exists():
                categories = video.categories.all()
                related_videos = Video.objects.filter(
                    categories__in=categories,
                    is_published=True
                ).exclude(id=video.id).distinct()[:6]
            else:
                # Fallback to videos from same creator
                related_videos = Video.objects.filter(
                    creator=video.creator,
                    is_published=True
                ).exclude(id=video.id)[:6]
                
            # If still no related videos, just get recent popular ones
            if not related_videos.exists():
                related_videos = Video.objects.filter(
                    is_published=True
                ).exclude(id=video.id).order_by('-views')[:6]
        except Exception:
            # Final fallback
            related_videos = Video.objects.filter(
                is_published=True
            ).exclude(id=video.id).order_by('-created_at')[:6]
    
    return render(request, 'videos/detail.html', {
        'video': video,
        'comments': comments,   
        'is_liked': is_liked,
        'is_subscribed': is_subscribed,
        'comment_form': CommentForm(),
        'related_videos': related_videos,
        'is_recommendation': is_recommendation,
        'rec_source': request.GET.get('rec_source', '')
    })

@login_required
def video_edit(request, slug):
    video = get_object_or_404(Video, slug=slug, creator=request.user)
    old_file = video.file.name if video.file else None
    
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES, instance=video)
        if form.is_valid():
            video = form.save(commit=False)
            
            # If file changed or content was significantly edited, reset moderation
            if 'file' in request.FILES or 'image' in request.FILES or 'title' in form.changed_data or 'description' in form.changed_data:
                video.requires_moderation = True
                video.moderation_status = 'pending'
                video.is_published = False
                messages.info(request, "Your content has been updated and will be reviewed before publishing.")
            
            # Make sure hls_url has a value - use empty string if not already set
            if video.hls_url is None:
                video.hls_url = ''
            
            # Check if video file was changed and if FFmpeg is available
            new_file = 'file' in request.FILES
            if new_file and video.content_type == 'video':
                # Mark as processing
                video.is_processing = True
                video.save()
                
                if check_ffmpeg():
                    # Get the path to the uploaded video file
                    video_path = os.path.join(settings.MEDIA_ROOT, video.file.name)
                    
                    # Process video with FFmpeg
                    success, result = convert_video_to_hls(video_path)
                    
                    if success:
                        # Update the video model with the HLS URL
                        video.hls_url = result
                        video.is_processing = False
                        video.save()
                    else:
                        # Still succeed but with a warning - but keep existing hls_url or empty string
                        video.is_processing = False
                        video.save()
                        messages.warning(request, f'Video updated but HLS conversion failed: {result}')
                else:
                    # FFmpeg not available
                    video.is_processing = False
                    video.save()
                    messages.warning(request, 'Video updated but HLS conversion is not available.')
            else:
                video.save()
            
            return redirect('videos:watch', slug=video.slug)
    else:
        form = VideoForm(instance=video)
    return render(request, 'videos/edit.html', {'form': form, 'video': video})

@login_required
def video_delete(request, slug):
    video = get_object_or_404(Video, slug=slug, creator=request.user)
    if request.method == 'POST':
        video.delete()
        messages.success(request, 'Video deleted successfully!')
        return redirect('users:channel', username=request.user.username)
    return render(request, 'videos/delete.html', {'video': video})

@login_required
def video_like(request, slug):
    try:
        video = get_object_or_404(Video, slug=slug)
        
        if request.method != 'POST':
            return JsonResponse({
                'success': False,
                'error': 'Invalid request method'
            }, status=405)
        
        # Check if like already exists
        existing_like = Like.objects.filter(video=video, user=request.user).first()
        
        if existing_like:
            # Unlike
            existing_like.delete()
            liked = False
        else:
            # Like
            Like.objects.create(video=video, user=request.user)
            create_notification(request.user, video.creator, 'like', video)
            liked = True
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'liked': liked,
                'like_count': video.like_count
            })
        
        # For non-AJAX requests
        if liked:
            messages.success(request, 'Video liked successfully!')
        else:
            messages.success(request, 'Video unliked successfully!')
        
        return redirect('videos:watch', slug=slug)
        
    except Exception as e:
        print(f"Error in video_like view: {str(e)}")  # For debugging
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def comment_video(request, slug):
    video = get_object_or_404(Video, slug=slug)
    if request.method == 'POST':
        text = request.POST.get('text')
        parent_id = request.POST.get('parent_id')
        
        if parent_id:
            parent_comment = get_object_or_404(Comment, id=parent_id)
            comment = Comment.objects.create(
                user=request.user,
                content=text,
                video=video,
                parent=parent_comment
            )
            create_notification(request.user, parent_comment.user, 'reply', comment)
        else:
            comment = Comment.objects.create(
                user=request.user,
                content=text,
                video=video
            )
            create_notification(request.user, video.creator, 'comment', comment)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'content': comment.content,
                    'user': {
                        'username': comment.user.username,
                        'avatar': comment.user.avatar.url if comment.user.avatar else '/static/images/default-avatar.png'
                    },
                    'created_at': comment.created_at.strftime('%b %d, %Y'),
                    'like_count': 0,
                    'is_liked_by_user': False
                }
            })
        
        messages.success(request, 'Comment added successfully!')
        return redirect('videos:watch', slug=slug)
    return redirect('videos:watch', slug=slug)

@login_required
def playlist_create(request):
    if request.method == 'POST':
        form = PlaylistForm(request.POST)
        if form.is_valid():
            playlist = form.save(commit=False)
            playlist.creator = request.user
            playlist.save()
            messages.success(request, 'Playlist created successfully!')
            return redirect('videos:playlist_detail', pk=playlist.pk)
    else:
        form = PlaylistForm()
    return render(request, 'videos/playlist_create.html', {'form': form})

def playlist_detail(request, pk):
    """
    View for showing playlist details
    """
    playlist = get_object_or_404(Playlist, pk=pk)
    
    # If the playlist is private, only the creator can view it
    if not playlist.is_public and request.user != playlist.creator:
        raise PermissionDenied
    
    # Get all items in this playlist, ordered by the 'order' field
    playlist_items = PlaylistItem.objects.filter(playlist=playlist).order_by('order')
    
    context = {
        'playlist': playlist,
        'playlist_items': playlist_items,
    }
    
    return render(request, 'videos/playlist.html', context)

@login_required
def playlist_edit(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk, creator=request.user)
    if request.method == 'POST':
        form = PlaylistForm(request.POST, instance=playlist)
        if form.is_valid():
            form.save()
            messages.success(request, 'Playlist updated successfully!')
            return redirect('videos:playlist_detail', pk=playlist.pk)
    else:
        form = PlaylistForm(instance=playlist)
    return render(request, 'videos/playlist_edit.html', {'form': form, 'playlist': playlist})

@login_required
def toggle_privacy(request, slug):
    video = get_object_or_404(Video, slug=slug, creator=request.user)
    if request.method == 'POST':
        video.is_published = not video.is_published
        video.save()
        status = 'public' if video.is_published else 'private'
        messages.success(request, f'Video is now {status}')
        return redirect('users:channel', username=request.user.username)
    return redirect('users:channel', username=request.user.username)

@login_required
def like_comment(request, comment_id):
    try:
        comment = get_object_or_404(Comment, id=comment_id)
        
        if request.method != 'POST':
            return JsonResponse({
                'success': False,
                'error': 'Invalid request method'
            }, status=405)
        
        # Toggle like using ManyToManyField
        if request.user in comment.likes.all():
            comment.likes.remove(request.user)
            liked = False
        else:
            comment.likes.add(request.user)
            create_notification(request.user, comment.user, 'like', comment)
            liked = True
        
        # Get fresh like count
        like_count = comment.likes.count()
        
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': like_count
        })
        
    except Exception as e:
        print(f"Error in like_comment view: {str(e)}")  # For debugging
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def edit_comment(request, comment_id):
    try:
        comment = get_object_or_404(Comment, id=comment_id, user=request.user)
        
        if request.method != 'POST':
            return JsonResponse({
                'success': False,
                'error': 'Invalid request method'
            }, status=405)
        
        # Get JSON data from request
        data = json.loads(request.body)
        new_content = data.get('content', '').strip()
        
        if not new_content:
            return JsonResponse({
                'success': False,
                'error': 'Comment content cannot be empty'
            }, status=400)
        
        # Update the comment
        comment.content = new_content
        comment.save()
        
        return JsonResponse({
            'success': True,
            'content': comment.content
        })
        
    except Exception as e:
        print(f"Error in edit_comment view: {str(e)}")  # For debugging
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def delete_comment(request, comment_id):
    try:
        comment = get_object_or_404(Comment, id=comment_id, user=request.user)
        
        if request.method != 'POST':
            return JsonResponse({
                'success': False,
                'error': 'Invalid request method'
            }, status=405)
        
        # Delete the comment
        comment.delete()
        
        return JsonResponse({
            'success': True
        })
        
    except Exception as e:
        print(f"Error in delete_comment view: {str(e)}")  # For debugging
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def playlist_delete(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk, creator=request.user)
    if request.method == 'POST':
        playlist.delete()
        messages.success(request, 'Playlist deleted successfully.')
        return redirect('users:channel', username=request.user.username)
    return redirect('videos:playlist_detail', pk=pk)

@login_required
def add_to_playlist(request, video_slug):
    """
    View to display a page where the user can add a video to their playlists or create a new playlist.
    """
    video = get_object_or_404(Video, slug=video_slug)
    
    # Get all playlists owned by the current user
    playlists = Playlist.objects.filter(creator=request.user).order_by('-created_at')
    
    # Track that the user has viewed this page
    VideoView.record_view(
        video=video,
        user=request.user,
        session_id=request.session.session_key,
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    context = {
        'video': video,
        'playlists': playlists,
    }
    
    return render(request, 'videos/add_to_playlist.html', context)

@login_required
def playlist_add_item(request, pk, video_slug):
    """
    Add a video to a specific playlist.
    """
    if request.method != 'POST':
        return redirect('videos:browse')
    
    playlist = get_object_or_404(Playlist, pk=pk, creator=request.user)
    video = get_object_or_404(Video, slug=video_slug)
    
    # Check if the video is already in the playlist
    if not PlaylistItem.objects.filter(playlist=playlist, video=video).exists():
        # Get the next order number
        next_order = PlaylistItem.objects.filter(playlist=playlist).count() + 1
        
        # Create a new playlist item
        PlaylistItem.objects.create(
            playlist=playlist,
            video=video,
            order=next_order
        )
    
    # Check if there's a redirect_to parameter
    redirect_to = request.POST.get('redirect_to')
    if redirect_to:
        return redirect(redirect_to)
    
    return redirect('videos:playlist', pk=pk)

@login_required
def playlist_remove_item(request, pk, video_pk):
    """
    Remove a video from a playlist.
    """
    if request.method != 'POST':
        return redirect('videos:browse')
    
    playlist = get_object_or_404(Playlist, pk=pk, creator=request.user)
    
    # Get the item and delete it
    try:
        item = PlaylistItem.objects.get(playlist=playlist, video_id=video_pk)
        order_removed = item.order
        item.delete()
        
        # Update the order of the remaining items
        for item in PlaylistItem.objects.filter(playlist=playlist, order__gt=order_removed).order_by('order'):
            item.order -= 1
            item.save()
            
    except PlaylistItem.DoesNotExist:
        pass
    
    # Check if there's a redirect_to parameter
    redirect_to = request.POST.get('redirect_to')
    if redirect_to:
        return redirect(redirect_to)
    
    # Redirect to the playlist page
    return redirect('videos:playlist', pk=pk)

def browse(request):
    videos = Video.objects.filter(is_published=True).order_by('-created_at')
    return render(request, 'videos/browse.html', {'videos': videos})

@login_required
def playlist_player(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk)
    
    # Check if user has access to this playlist
    if not playlist.is_public and playlist.creator != request.user:
        messages.error(request, 'This playlist is private.')
        return redirect('core:home')
    
    # Get all playlist items in order
    playlist_items = playlist.playlistitem_set.all().order_by('order')
    
    # Get the video to display (first one by default)
    video_id = request.GET.get('video')
    current_item = None
    
    if video_id:
        try:
            # Try to get the specific video
            current_item = playlist_items.get(video__id=video_id)
        except PlaylistItem.DoesNotExist:
            # If video doesn't exist in playlist, use first
            current_item = playlist_items.first() if playlist_items.exists() else None
    else:
        # No video specified, use first
        current_item = playlist_items.first() if playlist_items.exists() else None
    
    # Get current video
    current_video = current_item.video if current_item else None
    
    # Find next video for autoplay
    next_item = None
    if current_item:
        next_items = playlist_items.filter(order__gt=current_item.order).order_by('order')
        next_item = next_items.first() if next_items.exists() else None
    
    # Check if current video is liked
    is_liked = False
    is_subscribed = False
    if current_video and request.user.is_authenticated:
        from core.models import Like
        is_liked = Like.objects.filter(video=current_video, user=request.user).exists()
        is_subscribed = current_video.creator.subscribers.filter(id=request.user.id).exists()
    
    # Load comments if there's a current video
    comments = []
    if current_video:
        comments = current_video.comments.filter(parent=None)
        
        # Add like status to comments
        if request.user.is_authenticated:
            for comment in comments:
                comment.is_liked_by_user = comment.likes.filter(id=request.user.id).exists()
                for reply in comment.replies.all():
                    reply.is_liked_by_user = reply.likes.filter(id=request.user.id).exists()
    
    context = {
        'playlist': playlist,
        'playlist_items': playlist_items,
        'current_video': current_video,
        'video': current_video,
        'next_item': next_item,
        'is_liked': is_liked,
        'is_subscribed': is_subscribed,
        'comments': comments,
    }
    
    # Use the new template for video content, fall back to old template for other content types
    if current_video and current_video.content_type == 'video':
        return render(request, 'videos/playlist_player_new.html', context)
    return render(request, 'videos/playlist_player.html', context)

@login_required
def playlist_reorder(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk, creator=request.user)
    
    if request.method == 'POST':
        try:
            # Get the new order from the request
            new_order = request.POST.getlist('item_order[]')
            
            # Update the order of each item
            for i, item_id in enumerate(new_order, 1):
                item = PlaylistItem.objects.get(id=int(item_id), playlist=playlist)
                item.order = i
                item.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Only POST requests are allowed'})

@login_required
def fix_missing_slugs(request):
    """
    Utility view to fix content with missing or invalid slugs.
    Only processes content owned by the requesting user.
    """
    if request.method == 'POST':
        # Get all content owned by the user
        user_content = Video.objects.filter(creator=request.user)
        fixed_count = 0
        
        for content in user_content:
            if not content.slug or content.slug.strip() == '':
                # Create a slug from the title
                base_slug = slugify(content.title)
                
                # If slug is empty (e.g., title only had special characters), use content type + id
                if not base_slug:
                    base_slug = f"{content.content_type}-content"
                
                # Add random suffix to ensure uniqueness
                unique_id = str(uuid.uuid4())[:8]
                content.slug = f"{base_slug}-{unique_id}"
                content.save()
                fixed_count += 1
        
        if fixed_count > 0:
            messages.success(request, f"Successfully fixed slugs for {fixed_count} content items.")
        else:
            messages.info(request, "No content items with missing slugs were found.")
        
        # Redirect back to the channel page
        return redirect('users:channel', username=request.user.username)
    
    # If not a POST request, redirect to channel page
    return redirect('users:channel', username=request.user.username)

@require_POST
@login_required
def update_watch_time(request):
    """
    Update the watch time for a video and the recommendation engine stats.
    
    This endpoint is called periodically by the watch time tracker JS.
    """
    try:
        video_id = request.POST.get('video_id')
        watch_time = int(request.POST.get('watch_time', 0))
        
        # Get the video
        video = get_object_or_404(Video, id=video_id)
        
        # Update the VideoView record
        try:
            # Find the most recent view for this user and video
            view = VideoView.objects.filter(
                video=video,
                user=request.user,
                created_at__gte=timezone.now() - timezone.timedelta(hours=1)
            ).order_by('-created_at').first()
            
            if view:
                # Update existing view with new watch time
                view.view_time = max(view.view_time, watch_time)  # Use max to prevent decreasing
                view.save()
            else:
                # Create a new view record if none found
                VideoView.record_view(
                    video=video,
                    user=request.user,
                    session_id=request.session.session_key,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    view_time=watch_time,
                    referrer=request.META.get('HTTP_REFERER', ''),
                    device='mobile' if 'Mobile' in request.META.get('HTTP_USER_AGENT', '') else 'desktop',
                    is_recommendation='rec_source' in request.GET
                )
            
            # Update recommendation stats if this was a recommendation
            if 'rec_source' in request.GET:
                try:
                    from core.recommender import ContextualBanditRecommender
                    recommender = ContextualBanditRecommender()
                    recommender.update_stats(
                        video_id=video.id,
                        user_id=request.user.id,
                        clicked=True,
                        watch_time=watch_time
                    )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error updating recommendation stats: {e}")
            
            return JsonResponse({
                'success': True,
                'video_id': video.id,
                'watch_time': watch_time
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
