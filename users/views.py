from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from .models import CustomUser, Subscription, Notification, PasswordResetOTP, EmailVerificationOTP
from videos.models import Video, Playlist, VideoView
from core.models import Like, Comment
from django.db import models
from .forms import ProfileEditForm, SignupForm
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.safestring import mark_safe
from django.urls import reverse
import random

def profile(request, username):
    user = get_object_or_404(CustomUser, username=username)
    videos = Video.objects.filter(creator=user, is_published=True)
    playlists = Playlist.objects.filter(creator=user, is_public=True)
    is_subscribed = request.user.is_authenticated and user.subscribers.filter(id=request.user.id).exists()
    
    # Get content stats
    video_count = Video.objects.filter(creator=user, content_type='video').count()
    photo_count = Video.objects.filter(creator=user, content_type='photo').count()
    blog_count = Video.objects.filter(creator=user, content_type='blog').count()
    total_views = Video.objects.filter(creator=user).aggregate(Sum('views'))['views__sum'] or 0
    total_likes = Like.objects.filter(video__creator=user).count()
    
    # Get history and liked content for the profile owner
    history_items = []
    liked_content = []
    if request.user.is_authenticated and request.user == user:
        history_items = VideoView.objects.filter(user=request.user).order_by('-created_at')[:10]
        liked_content = Like.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    return render(request, 'users/profile.html', {
        'profile': user,
        'videos': videos,
        'playlists': playlists,
        'is_subscribed': is_subscribed,
        'video_count': video_count,
        'photo_count': photo_count,
        'blog_count': blog_count,
        'total_views': total_views,
        'total_likes': total_likes,
        'history_items': history_items,
        'liked_content': liked_content
    })

@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile', username=request.user.username)
    else:
        form = ProfileEditForm(instance=request.user)
    
    return render(request, 'users/profile_edit.html', {'form': form})

def channel(request, username):
    channel_user = get_object_or_404(CustomUser, username=username, is_active=True)
    
    # Get content created by the user, filtered by content type
    # If own channel or admin, include unpublished content. Otherwise only show published content.
    if request.user == channel_user or (request.user.is_authenticated and request.user.is_staff):
        # Show all content including unpublished for the channel owner or admins
        videos = Video.objects.filter(creator=channel_user, content_type='video').order_by('-created_at')
        photos = Video.objects.filter(creator=channel_user, content_type='photo').order_by('-created_at')
        blogs = Video.objects.filter(creator=channel_user, content_type='blog').order_by('-created_at')
        
        # Debug information
        print(f"DEBUG - User viewing own channel: {username}")
        print(f"DEBUG - Videos count: {videos.count()}")
        print(f"DEBUG - Photos count: {photos.count()}")
        print(f"DEBUG - Blogs count: {blogs.count()}")
        
        # Check if photos have valid image fields
        for photo in photos:
            print(f"DEBUG - Photo ID {photo.id}, title: {photo.title}, image exists: {bool(photo.image)}")
            if not photo.image:
                print(f"DEBUG - WARNING: Photo ID {photo.id} missing image field!")
                
        # Check if blogs have valid thumbnail fields
        for blog in blogs:
            print(f"DEBUG - Blog ID {blog.id}, title: {blog.title}, thumbnail exists: {bool(blog.thumbnail)}")
            if not blog.thumbnail:
                print(f"DEBUG - WARNING: Blog ID {blog.id} missing thumbnail!")
    else:
        # Only show published content to other users
        videos = Video.objects.filter(creator=channel_user, content_type='video', is_published=True).order_by('-created_at')
        photos = Video.objects.filter(creator=channel_user, content_type='photo', is_published=True).order_by('-created_at')
        blogs = Video.objects.filter(creator=channel_user, content_type='blog', is_published=True).order_by('-created_at')
    
    # Get public playlists or all playlists if viewing own channel or admin
    if request.user == channel_user or (request.user.is_authenticated and request.user.is_staff):
        playlists = Playlist.objects.filter(creator=channel_user).order_by('-created_at')
    else:
        playlists = Playlist.objects.filter(creator=channel_user, is_public=True).order_by('-created_at')
    
    # Check if the current user is subscribed to the channel
    is_subscribed = False
    if request.user.is_authenticated and request.user != channel_user:
        is_subscribed = channel_user.subscribers.filter(id=request.user.id).exists()
    
    # Count stats
    videos_count = videos.count()
    photos_count = photos.count()
    blogs_count = blogs.count()
    playlists_count = playlists.count()
    total_views = Video.objects.filter(creator=channel_user).aggregate(Sum('views'))['views__sum'] or 0
    total_likes = Like.objects.filter(video__creator=channel_user).count()
    
    context = {
        'channel': channel_user,
        'videos': videos,
        'photos': photos,
        'blogs': blogs,
        'playlists': playlists,
        'is_subscribed': is_subscribed,
        'content_count': videos_count + photos_count + blogs_count,
        'videos_count': videos_count,
        'photos_count': photos_count,
        'blogs_count': blogs_count,
        'playlists_count': playlists_count,
        'total_views': total_views,
        'total_likes': total_likes,
    }
    
    # Add debug information to the context for template debugging
    if request.user == channel_user:
        context['debug_info'] = {
            'videos_count': videos_count,
            'photos_count': photos_count,
            'blogs_count': blogs_count,
            'photos_data': [{'id': p.id, 'title': p.title, 'has_image': bool(p.image)} for p in photos[:3]],
            'blogs_data': [{'id': b.id, 'title': b.title, 'has_thumbnail': bool(b.thumbnail)} for b in blogs[:3]],
        }
    
    return render(request, 'users/channel.html', context)

@login_required
def subscribe(request, username):
    user_to_subscribe = get_object_or_404(CustomUser, username=username)
    
    if request.method == 'POST':
        if request.user == user_to_subscribe:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'You cannot subscribe to yourself'})
            messages.error(request, "You cannot subscribe to yourself.")
            return redirect('users:channel', username=username)
            
        try:
            is_subscribed = user_to_subscribe.subscribers.filter(id=request.user.id).exists()
            if is_subscribed:
                user_to_subscribe.subscribers.remove(request.user)
                message = f'Unsubscribed from {username}'
                subscribed = False
            else:
                user_to_subscribe.subscribers.add(request.user)
                message = f'Subscribed to {username}'
                subscribed = True
                
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'subscribed': subscribed,
                    'message': message,
                    'subscriber_count': user_to_subscribe.subscriber_count
                })
                
            messages.success(request, message)
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            messages.error(request, "An error occurred while processing your subscription.")
            
    return redirect('users:channel', username=username)

@login_required
def notifications(request):
    notifications = Notification.objects.filter(recipient=request.user)
    return render(request, 'users/notifications.html', {'notifications': notifications})

def create_notification(sender, recipient, notification_type, content_object):
    if sender != recipient:  # Don't create notifications for your own actions
        Notification.objects.create(
            sender=sender,
            recipient=recipient,
            notification_type=notification_type,
            content_type=ContentType.objects.get_for_model(content_object),
            object_id=content_object.id
        )

@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.read = True
    notification.save()
    return redirect(notification.get_absolute_url())

@login_required
def user_profile(request):
    """
    User profile page showing watch history, liked content, and playlists
    """
    user = request.user
    
    # Get recent watch history (last 20 items)
    history_items = VideoView.objects.filter(
        user=user
    ).select_related('video').order_by('-created_at')[:20]
    
    # Get recent liked content (last 20 items)
    liked_content = Like.objects.filter(
        user=user
    ).select_related('video').order_by('-created_at')[:20]
    
    # Get user's playlists
    playlists = Playlist.objects.filter(
        creator=user
    ).prefetch_related('playlist_items').order_by('-created_at')
    
    # Count content by type
    video_count = Video.objects.filter(creator=user, content_type='video').count()
    photo_count = Video.objects.filter(creator=user, content_type='photo').count()
    blog_count = Video.objects.filter(creator=user, content_type='blog').count()
    
    # Count total views and likes
    total_views = Video.objects.filter(creator=user).aggregate(Sum('views'))['views__sum'] or 0
    total_likes = Like.objects.filter(video__creator=user).count()
    
    context = {
        'profile': user,
        'history_items': history_items,
        'liked_content': liked_content,
        'playlists': playlists,
        'video_count': video_count,
        'photo_count': photo_count,
        'blog_count': blog_count,
        'total_views': total_views,
        'total_likes': total_likes,
    }
    
    return render(request, 'users/profile.html', context)

def debug_content(request):
    """Debug view to display all photos and blogs in the database."""
    photos = Video.objects.filter(content_type='photo')
    blogs = Video.objects.filter(content_type='blog')
    
    response = "DEBUG INFO:<br/><br/>"
    
    response += f"<h2>Photos ({photos.count()}):</h2>"
    for photo in photos:
        response += f"<div style='margin-bottom:20px; border:1px solid #ccc; padding:10px;'>"
        response += f"<strong>ID:</strong> {photo.id}<br/>"
        response += f"<strong>Title:</strong> {photo.title}<br/>"
        response += f"<strong>Creator:</strong> {photo.creator.username}<br/>"
        response += f"<strong>Published:</strong> {photo.is_published}<br/>"
        response += f"<strong>Image Path:</strong> {photo.image.name if photo.image else 'None'}<br/>"
        if photo.image:
            response += f"<img src='/media/{photo.image.name}' style='max-width:300px;'><br/>"
        response += f"<strong>Created:</strong> {photo.created_at}<br/>"
        response += "</div>"
    
    response += f"<h2>Blogs ({blogs.count()}):</h2>"
    for blog in blogs:
        response += f"<div style='margin-bottom:20px; border:1px solid #ccc; padding:10px;'>"
        response += f"<strong>ID:</strong> {blog.id}<br/>"
        response += f"<strong>Title:</strong> {blog.title}<br/>"
        response += f"<strong>Creator:</strong> {blog.creator.username}<br/>"
        response += f"<strong>Published:</strong> {blog.is_published}<br/>"
        response += f"<strong>Thumbnail Path:</strong> {blog.thumbnail.name if blog.thumbnail else 'None'}<br/>"
        if blog.thumbnail:
            response += f"<img src='/media/{blog.thumbnail.name}' style='max-width:300px;'><br/>"
        response += f"<strong>Blog Content:</strong> {blog.blog_content[:100]}...<br/>"
        response += f"<strong>Created:</strong> {blog.created_at}<br/>"
        response += "</div>"
        
    return HttpResponse(response)

def password_reset_request(request):
    """View to request password reset using OTP"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'users/password_reset_request.html')
        
        # Find user with this email
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
            
            # Generate OTP
            otp_obj = PasswordResetOTP.generate_otp(user)
            
            # Send email with OTP
            context = {
                'user': user,
                'otp': otp_obj.otp,
                'expiry_time': '15 minutes',
            }
            
            email_subject = 'Your Password Reset OTP'
            email_body = render_to_string('users/emails/password_reset_otp_email.html', context)
            
            send_mail(
                email_subject,
                '',  # Plain text version (not used)
                None,  # From Email (uses DEFAULT_FROM_EMAIL)
                [user.email],
                html_message=email_body,
                fail_silently=False,
            )
            
            # Store user ID in session for the next step
            request.session['reset_user_id'] = user.id
            
            messages.success(request, 
                mark_safe(f'An OTP has been sent to <strong>{email}</strong>. Please check your email and enter the 6-digit code below.'))
            return redirect('users:password_reset_verify_otp')
            
        except User.DoesNotExist:
            # Don't reveal that the user doesn't exist
            messages.success(request, 
                mark_safe('If the email address exists in our database, you will receive a password recovery OTP shortly.'))
            return render(request, 'users/password_reset_request.html')
    
    return render(request, 'users/password_reset_request.html')

def password_reset_verify_otp(request):
    """View to verify OTP and allow user to reset password"""
    # Check if we have a user ID in session
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Password reset session expired. Please start again.')
        return redirect('users:password_reset_request')
    
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Invalid password reset request. Please try again.')
        return redirect('users:password_reset_request')
    
    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        
        if not otp or len(otp) != 6:
            messages.error(request, 'Please enter a valid 6-digit OTP.')
            return render(request, 'users/password_reset_verify_otp.html')
        
        # Find valid OTP for this user
        try:
            otp_obj = PasswordResetOTP.objects.get(
                user=user, 
                otp=otp,
                is_used=False
            )
            
            if not otp_obj.is_valid():
                messages.error(request, 'This OTP has expired. Please request a new one.')
                return redirect('users:password_reset_request')
            
            # OTP is valid, allow password reset
            # Mark the OTP as used
            otp_obj.is_used = True
            otp_obj.save()
            
            # Store in session that OTP was verified
            request.session['otp_verified'] = True
            
            return redirect('users:password_reset_confirm')
            
        except PasswordResetOTP.DoesNotExist:
            messages.error(request, 'Invalid OTP. Please check and try again.')
            return render(request, 'users/password_reset_verify_otp.html')
    
    return render(request, 'users/password_reset_verify_otp.html')

def password_reset_confirm(request):
    """View to set new password after OTP verification"""
    # Check if OTP was verified
    user_id = request.session.get('reset_user_id')
    otp_verified = request.session.get('otp_verified', False)
    
    if not user_id or not otp_verified:
        messages.error(request, 'Invalid password reset request. Please start again.')
        return redirect('users:password_reset_request')
    
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Invalid password reset request. Please try again.')
        return redirect('users:password_reset_request')
    
    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        if not password1 or len(password1) < 8:
            messages.error(request, 'Please enter a password of at least 8 characters.')
            return render(request, 'users/password_reset_confirm.html')
            
        if password1 != password2:
            messages.error(request, 'Passwords do not match. Please try again.')
            return render(request, 'users/password_reset_confirm.html')
        
        # Set new password
        user.set_password(password1)
        user.save()
        
        # Clear session data
        if 'reset_user_id' in request.session:
            del request.session['reset_user_id']
        if 'otp_verified' in request.session:
            del request.session['otp_verified']
        
        messages.success(request, 'Your password has been reset successfully. You can now log in with your new password.')
        return redirect('account_login')
    
    return render(request, 'users/password_reset_confirm.html')

# Admin-initiated password reset
@login_required
def admin_password_reset(request, user_id):
    """View for admins to send password reset links to users"""
    if not request.user.is_admin:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('custom_admin:user_list')
    
    User = get_user_model()
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('custom_admin:user_list')
    
    # Generate token
    token = default_token_generator.make_token(target_user)
    uid = urlsafe_base64_encode(force_bytes(target_user.pk))
    
    # Build reset URL
    reset_url = request.build_absolute_uri(
        reverse('users:password_reset_from_admin', args=[uid, token])
    )
    
    # Send email with reset link
    context = {
        'user': target_user,
        'reset_url': reset_url,
        'expiry_time': '24 hours',
        'admin_name': request.user.username,
    }
    
    email_subject = 'Password Reset Requested by Admin'
    email_body = render_to_string('users/emails/admin_password_reset_email.html', context)
    
    send_mail(
        email_subject,
        '',  # Plain text version (not used)
        None,  # From Email (uses DEFAULT_FROM_EMAIL)
        [target_user.email],
        html_message=email_body,
        fail_silently=False,
    )
    
    messages.success(request, f'Password reset link has been sent to {target_user.email}.')
    return redirect('custom_admin:user_detail', user_id=user_id)

def password_reset_from_admin(request, uidb64, token):
    """View for users to reset their password from admin-initiated reset"""
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None
    
    # Check if token is valid
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password1 = request.POST.get('password1', '')
            password2 = request.POST.get('password2', '')
            
            if not password1 or len(password1) < 8:
                messages.error(request, 'Please enter a password of at least 8 characters.')
                return render(request, 'users/password_reset_from_admin.html')
                
            if password1 != password2:
                messages.error(request, 'Passwords do not match. Please try again.')
                return render(request, 'users/password_reset_from_admin.html')
            
            # Set new password
            user.set_password(password1)
            user.save()
            
            messages.success(request, 'Your password has been reset successfully. You can now log in with your new password.')
            return redirect('account_login')
        
        return render(request, 'users/password_reset_from_admin.html')
    else:
        messages.error(request, 'The password reset link is invalid or has expired. Please request a new one.')
        return redirect('account_login')

def pre_signup_email_verification(request):
    """
    Handles the initial verification of email before signup
    This is the first step in the registration process
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        
        # Check if email already exists in the system
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'This email is already registered. Please log in instead.')
            return redirect('account_login')
        
        # Generate OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Store email and OTP in session for verification
        request.session['signup_email'] = email
        request.session['signup_email_otp'] = otp
        request.session['signup_email_verified'] = False
        
        # Send email with styled template
        context = {
            'otp': otp,
            'expiry_time': '15 minutes',
        }
        
        email_subject = 'Email Verification OTP for YTC Signup'
        email_body = render_to_string('users/emails/verification_email.html', context)
        
        send_mail(
            email_subject,
            '',  # Plain text version (not used)
            None,  # From Email (uses DEFAULT_FROM_EMAIL)
            [email],
            html_message=email_body,
            fail_silently=False,
        )
        
        messages.success(request, 'Verification OTP has been sent to your email.')
        return redirect('users:verify_signup_otp')
    
    return render(request, 'users/pre_signup_verification.html')

def verify_signup_otp(request):
    """
    Verifies the OTP sent to the email before signup
    This is the second step in the registration process
    """
    # Check if we have an email in session
    email = request.session.get('signup_email')
    if not email:
        messages.error(request, 'Email verification session expired. Please start again.')
        return redirect('users:pre_signup_email_verification')
    
    if request.method == 'POST':
        otp = request.POST.get('otp')
        session_otp = request.session.get('signup_email_otp')
        
        if otp == session_otp:
            # Mark email as verified in session
            request.session['signup_email_verified'] = True
            
            # Redirect to the signup page with verified email
            messages.success(request, 'Email verified successfully! Please complete your registration.')
            return redirect('account_signup')
        else:
            messages.error(request, 'Invalid OTP. Please check and try again.')
    
    context = {
        'email': email
    }
    return render(request, 'users/verify_signup_otp.html', context)
