from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from users.models import CustomUser, AdminRole
from videos.models import Video
from core.models import Report
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
import random
from django.core.paginator import Paginator
from django.urls import reverse
from notifications.models import Notification
from core.models import AdminLog

@login_required
def dashboard(request):
    """Display the admin dashboard with statistics and quick access links."""
    # Check if the user is authorized to access the admin dashboard
    if not request.user.is_authenticated or not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        messages.error(request, "You do not have permission to access the admin area.")
        return redirect('core:home')
    
    # Get common statistics
    total_videos = Video.objects.count()
    total_users = CustomUser.objects.count()
    
    # Prepare context
    context = {
        'admin_section': 'dashboard',
        'total_videos': total_videos,
        'total_users': total_users,
        'now': timezone.now(),
    }
    
    # Super Admin specific data
    if request.user.admin_role.level == 1:
        # Add Super Admin specific stats
        admin_users = CustomUser.objects.filter(is_admin=True).count()
        total_reports = 0  # You would need to implement a reporting system
        
        context.update({
            'admin_users': admin_users,
            'total_reports': total_reports,
            'system_health': {
                'server_load': random.randint(20, 85),
                'storage': random.randint(30, 90),
                'bandwidth': random.randint(25, 95)
            },
            'escalated_issues': []
        })
    
    # Moderator specific data
    if request.user.admin_role.level == 2:
        # Add Moderator specific stats
        pending_reviews = 5  # Placeholder - implement actual flagged content count
        recent_flags = 12    # Placeholder
        
        context.update({
            'pending_reviews': pending_reviews,
            'recent_flags': recent_flags,
            'flagged_content': []  # Placeholder for flagged content
        })
    
    # Support Staff specific data
    if request.user.admin_role.level == 3:
        # Add Support Staff specific stats
        new_users = CustomUser.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=1)
        ).count()
        
        context.update({
            'new_users': new_users,
            'recent_support_requests': random.randint(0, 10)  # Placeholder
        })
    
    return render(request, 'custom_admin/dashboard.html', context)

@login_required
def user_list(request):
    """Display a list of users with filtering options."""
    # Check if user has permission to manage users
    if not request.user.is_admin or request.user.admin_role.level > 3:
        messages.error(request, "You do not have permission to access user management.")
        return redirect('custom_admin:dashboard')
    
    # Get filter parameter
    filter_type = request.GET.get('filter', 'all')
    
    # Base queryset
    users = CustomUser.objects.all()
    
    # Apply filters
    if filter_type == 'active':
        users = users.filter(is_active=True, last_login__gte=timezone.now() - timezone.timedelta(days=30))
    elif filter_type == 'inactive':
        users = users.filter(Q(is_active=False) | Q(last_login__lt=timezone.now() - timezone.timedelta(days=90)))
    elif filter_type == 'new':
        users = users.filter(date_joined__gte=timezone.now() - timezone.timedelta(days=7))
    elif filter_type == 'admin':
        users = users.filter(is_admin=True)
    elif filter_type == 'warning':
        # Placeholder - you would implement this based on your user warning system
        pass
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'admin_section': 'users',
        'filter_type': filter_type,
        'page_obj': page_obj,
    }
    
    return render(request, 'custom_admin/user_list.html', context)

@login_required
def user_detail(request, user_id):
    # Check if user has permission to manage users
    if not request.user.is_admin or request.user.admin_role.level > 3:
        messages.error(request, "You do not have permission to manage users.")
        return redirect('custom_admin:dashboard')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Handle POST requests for user updates
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            # Update user profile
            user.username = request.POST.get('username', user.username)
            user.email = request.POST.get('email', user.email)
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            
            # Update admin status if super admin
            if request.user.admin_role.level == 1:
                is_admin = request.POST.get('admin_status') == 'admin'
                if is_admin != user.is_admin:
                    user.is_admin = is_admin
                    if is_admin and request.POST.get('admin_role'):
                        # Assign admin role
                        role_level = int(request.POST.get('admin_role', 3))
                        role = AdminRole.objects.filter(level=role_level).first()
                        if role:
                            user.admin_role = role
                    elif not is_admin:
                        user.admin_role = None
            
            # Update active status
            is_active = request.POST.get('account_status') == 'active'
            if is_active != user.is_active:
                user.is_active = is_active
            
            # Send password reset if requested
            if request.POST.get('reset_password'):
                # This would typically use Django's password reset functionality
                # For now, just log the action
                print(f"Password reset requested for user {user.username}")
            
            user.save()
            messages.success(request, f"User {user.username} updated successfully.")
            return redirect('custom_admin:user_detail', user_id=user.id)
        
        elif action == 'toggle_active':
            # Toggle user active status
            user.is_active = not user.is_active
            user.save()
            status = "activated" if user.is_active else "deactivated"
            messages.success(request, f"User {user.username} {status} successfully.")
            return redirect('custom_admin:user_detail', user_id=user.id)
        
        elif action == 'send_warning':
            # Implement warning functionality
            warning_message = request.POST.get('warning_message', '')
            if warning_message:
                # This would typically create a warning record and notify the user
                # For now, just log the action
                print(f"Warning sent to {user.username}: {warning_message}")
                messages.success(request, f"Warning sent to {user.username}.")
            else:
                messages.error(request, "Warning message cannot be empty.")
            return redirect('custom_admin:user_detail', user_id=user.id)
        
        elif action == 'save_notes':
            # Save admin notes about the user
            notes = request.POST.get('admin_notes', '')
            # This would typically save to a notes model associated with the user
            # For now, just log the action
            print(f"Admin notes saved for {user.username}: {notes}")
            messages.success(request, f"Notes saved for {user.username}.")
            return redirect('custom_admin:user_detail', user_id=user.id)
            
        # Handle admin privilege actions (Super Admin only)
        elif action in ['promote_admin', 'remove_admin', 'change_role', 'delete_user']:
            # Check if the current user is a super admin
            if not request.user.is_super_admin:
                messages.error(request, "Only Super Admins can modify admin privileges.")
                return redirect('custom_admin:user_detail', user_id=user.id)
                
            if action == 'promote_admin':
                # Promote user to admin
                user.is_admin = True
                role_level = int(request.POST.get('admin_role', 3))  # Default to Support Staff
                role = AdminRole.objects.filter(level=role_level).first()
                if role:
                    user.admin_role = role
                    user.save()
                    messages.success(request, f"{user.username} has been promoted to {role.name}.")
                else:
                    messages.error(request, "Invalid admin role selected.")
                    
            elif action == 'remove_admin':
                # Remove admin privileges
                user.is_admin = False
                user.admin_role = None
                user.save()
                messages.success(request, f"Admin privileges removed from {user.username}.")
                
            elif action == 'change_role':
                # Change admin role
                if user.is_admin:
                    role_level = int(request.POST.get('admin_role', 3))
                    role = AdminRole.objects.filter(level=role_level).first()
                    if role:
                        user.admin_role = role
                        user.save()
                        messages.success(request, f"{user.username}'s role changed to {role.name}.")
                    else:
                        messages.error(request, "Invalid admin role selected.")
                else:
                    messages.error(request, "User must be an admin to change their role.")
                    
            elif action == 'delete_user':
                # Delete user account
                username = user.username
                user.delete()
                messages.success(request, f"User {username} has been permanently deleted.")
                return redirect('custom_admin:user_list')
                
            return redirect('custom_admin:user_detail', user_id=user.id)
    
    # Get user statistics and content
    video_count = Video.objects.filter(creator=user).count()
    videos = Video.objects.filter(creator=user).order_by('-created_at')[:5]
    
    context = {
        'admin_section': 'users',
        'user': user,
        'video_count': video_count,
        'videos': videos,
    }
    
    return render(request, 'custom_admin/user_detail.html', context)

@login_required
def toggle_user_active(request, user_id):
    """Quickly toggle a user's active status from the list view."""
    # Check if user has permission to manage users
    if not request.user.is_admin or request.user.admin_role.level > 3:
        messages.error(request, "You do not have permission to manage users.")
        return redirect('custom_admin:dashboard')
    
    if request.method == 'POST':
        user = get_object_or_404(CustomUser, id=user_id)
        user.is_active = not user.is_active
        user.save()
        status = "activated" if user.is_active else "deactivated"
        messages.success(request, f"User {user.username} {status} successfully.")
    
    return redirect('custom_admin:user_list')

@login_required
def send_email_to_users(request):
    """Send emails to selected users or user groups."""
    # Check if user has permission to manage users
    if not request.user.is_admin or request.user.admin_role.level > 3:
        messages.error(request, "You do not have permission to manage users.")
        return redirect('custom_admin:dashboard')
    
    if request.method == 'POST':
        recipients = request.POST.get('recipients', 'all')
        subject = request.POST.get('subject', '')
        message = request.POST.get('message', '')
        send_copy = request.POST.get('send_copy', False)
        
        if not subject or not message:
            messages.error(request, "Subject and message are required.")
            return redirect('custom_admin:user_list')
        
        # Get user emails based on recipient selection
        emails = []
        if recipients == 'all':
            emails = CustomUser.objects.values_list('email', flat=True)
        elif recipients == 'active':
            emails = CustomUser.objects.filter(is_active=True).values_list('email', flat=True)
        elif recipients == 'inactive':
            emails = CustomUser.objects.filter(is_active=False).values_list('email', flat=True)
        elif recipients == 'new':
            one_week_ago = timezone.now() - timezone.timedelta(days=7)
            emails = CustomUser.objects.filter(date_joined__gte=one_week_ago).values_list('email', flat=True)
        
        # This would typically use Django's email functionality
        # For now, just log the action
        print(f"Sending email to {len(emails)} users with subject: {subject}")
        if send_copy:
            emails.append(request.user.email)
        
        messages.success(request, f"Email sent to {len(emails)} users.")
    
    return redirect('custom_admin:user_list')

@login_required
def content_list(request):
    """Display a list of content with filtering options."""
    # Check if user has permission to manage content
    if not request.user.is_admin or request.user.admin_role.level > 2:
        messages.error(request, "You do not have permission to access content management.")
        return redirect('custom_admin:dashboard')
    
    # Handle bulk actions
    if request.method == 'POST':
        action = request.POST.get('bulk_action')
        selected_ids = request.POST.getlist('selected_content')
        moderation_notes = request.POST.get('moderation_notes', '')
        notify_creators = request.POST.get('notify_creators') == '1'
        send_warning = request.POST.get('send_warning') == '1'
        warning_message = request.POST.get('warning_message', '')
        
        if selected_ids and action:
            count = 0
            for content_id in selected_ids:
                try:
                    content = Video.objects.get(id=content_id)
                    
                    if action == 'approve':
                        content.moderation_status = 'approved'
                        content.requires_moderation = False
                        content.is_published = True
                        status_message = "approved"
                    elif action == 'reject':
                        content.moderation_status = 'rejected'
                        content.is_published = False
                        status_message = "rejected"
                    elif action == 'publish':
                        content.is_published = True
                        status_message = "published"
                    elif action == 'unpublish':
                        content.is_published = False
                        status_message = "unpublished"
                    elif action == 'delete':
                        content.delete()
                        count += 1
                        continue
                    
                    if moderation_notes:
                        content.moderation_notes = moderation_notes
                    
                    content.moderated_by = request.user
                    content.moderated_at = timezone.now()
                    content.save()
                    
                    # Send notification if enabled
                    if content.creator:
                        try:
                            # Import at the top level instead
                            from notifications.models import Notification
                            
                            # Standard notification for moderation actions
                            if notify_creators and action in ['approve', 'reject', 'publish', 'unpublish']:
                                # Create default message if none provided
                                default_message = ""
                                if action == 'approve':
                                    default_message = f"Your content '{content.title}' has been approved by our moderation team and is now visible to the community."
                                elif action == 'reject':
                                    default_message = f"Your content '{content.title}' has been rejected by our moderation team for not meeting our community guidelines."
                                elif action == 'publish':
                                    default_message = f"Your content '{content.title}' has been published and is now visible to the community."
                                elif action == 'unpublish':
                                    default_message = f"Your content '{content.title}' has been unpublished and is no longer visible to the community."
                                
                                notification_message = moderation_notes if moderation_notes else default_message
                                
                                Notification.objects.create(
                                    recipient=content.creator,
                                    actor=request.user,
                                    verb=f"Your content has been {status_message}",
                                    description=notification_message,
                                    content_type=ContentType.objects.get_for_model(content),
                                    object_id=content.id,
                                    notification_type='moderation',
                                    url=f"/videos/{content.id}/"
                                )
                            
                            # Separate warning notification if enabled
                            if send_warning and warning_message:
                                Notification.objects.create(
                                    recipient=content.creator,
                                    actor=request.user,
                                    verb=f"Warning about your content",
                                    description=warning_message,
                                    content_type=ContentType.objects.get_for_model(content),
                                    object_id=content.id,
                                    notification_type='warning',
                                    url=f"/videos/{content.id}/"
                                )
                                
                                # Log the warning for admin records
                                AdminLog.objects.create(
                                    admin=request.user,
                                    action_type="warning",
                                    description=f"Warning sent to {content.creator.username} about content '{content.title}': {warning_message[:100]}{'...' if len(warning_message) > 100 else ''}",
                                    content_type=ContentType.objects.get_for_model(content),
                                    object_id=content.id,
                                    target_user=content.creator
                                )
                                
                                messages.info(request, f"Warning sent to {content.creator.username} regarding '{content.title}'")
                        except Exception as e:
                            print(f"Failed to send notification for content {content.id}: {str(e)}")
                    
                    count += 1
                except Video.DoesNotExist:
                    continue
            
            action_display = action.replace('_', ' ').title()
            messages.success(request, f"Successfully {action_display}d {count} content items")
            
            # Redirect to the same filter or to the pending moderation filter if approving/rejecting
            if action in ['approve', 'reject']:
                return redirect(reverse('custom_admin:content_list') + '?filter=pending_moderation')
            return redirect(request.get_full_path())
    
    # Get filter parameters
    filter_type = request.GET.get('filter', 'all')
    content_type = request.GET.get('type', 'all')
    
    # Base queryset - using creator instead of user
    contents = Video.objects.select_related('creator').all()
    
    # Count by content type for the stats
    video_count = Video.objects.filter(content_type='video').count()
    photo_count = Video.objects.filter(content_type='photo').count()
    blog_count = Video.objects.filter(content_type='blog').count()
    
    # Apply filters
    if filter_type == 'reported':
        # Find content that has pending reports
        try:
            # First get the content type for videos
            video_ct = ContentType.objects.get_for_model(Video)
            
            # Get all reports for videos
            reports = Report.objects.filter(
                content_type=video_ct,
                status__in=['pending', 'reviewed']
            )
            
            # Manually extract the object_ids
            reported_ids = []
            for report in reports:
                reported_ids.append(report.object_id)
            
            # Filter the videos
            if reported_ids:
                contents = contents.filter(id__in=reported_ids)
            else:
                # No reports found, return empty queryset
                contents = Video.objects.none()
        except Exception as e:
            # If there's any error, log it and show empty results
            print(f"Error in reported content filter: {e}")
            contents = Video.objects.none()
            
    elif filter_type == 'pending_moderation':
        # Videos that require moderation
        contents = contents.filter(
            requires_moderation=True,
            moderation_status='pending'
        )
    elif filter_type == 'trending':
        # Ordering by views or recent popularity
        contents = contents.order_by('-views')
    elif filter_type == 'no_user':
        # Filter for videos without users (for admin cleanup)
        contents = contents.filter(creator__isnull=True)
    
    if content_type != 'all':
        # Filter by content type if you have multiple types
        contents = contents.filter(content_type=content_type)
    
    # Pagination
    paginator = Paginator(contents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'admin_section': 'content',
        'filter_type': filter_type,
        'content_type': content_type,
        'page_obj': page_obj,
        'video_count': video_count,
        'photo_count': photo_count,
        'blog_count': blog_count,
    }
    
    return render(request, 'custom_admin/content_list.html', context)

@login_required
def content_detail(request, video_id):
    # Check if user has permission to manage content
    if not request.user.is_admin or request.user.admin_role.level > 2:
        messages.error(request, "You do not have permission to manage content.")
        return redirect('custom_admin:dashboard')
    
    video = get_object_or_404(Video, id=video_id)
    
    # Handle POST requests for content updates
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_content':
            # Update video details
            video.title = request.POST.get('title', video.title)
            video.description = request.POST.get('description', video.description)
            video.is_published = request.POST.get('is_published') == 'on'
            
            # Ensure moderation_status is never NULL before saving
            if video.moderation_status is None:
                # Default to the previous status, or 'pending' if that's unavailable
                try:
                    old_video = Video.objects.get(id=video_id)
                    video.moderation_status = old_video.moderation_status
                except:
                    video.moderation_status = 'pending'
            
            video.save()
            messages.success(request, f"Content '{video.title}' updated successfully.")
            return redirect('custom_admin:content_detail', video_id=video.id)
        
        elif action == 'moderate_content':
            # Update moderation status
            moderation_status = request.POST.get('moderation_status')
            current_moderation_status = request.POST.get('current_moderation_status')
            moderation_notes = request.POST.get('moderation_notes', '')
            moderation_action = request.POST.get('moderation_action', 'save')
            notify_creator = request.POST.get('notify_creator') == '1'
            creator_message = request.POST.get('creator_message', '')
            
            # Use moderation_status if provided, otherwise use current_moderation_status
            # This ensures we never have a NULL value
            if moderation_status:
                video.moderation_status = moderation_status
            elif current_moderation_status:
                video.moderation_status = current_moderation_status
                
            # Always update the notes, moderator, and timestamp
            video.moderation_notes = moderation_notes
            video.moderated_by = request.user
            video.moderated_at = timezone.now()
            
            # Handle different moderation actions
            if moderation_action == 'approve_publish':
                video.moderation_status = 'approved'
                video.is_published = True
                video.requires_moderation = False
                messages.success(request, f"Content '{video.title}' has been approved and published.")
            elif moderation_action == 'reject_unpublish':
                video.moderation_status = 'rejected'
                video.is_published = False
                messages.success(request, f"Content '{video.title}' has been rejected and unpublished.")
            elif moderation_action == 'publish':
                # Just publish, don't change moderation status
                video.is_published = True
                messages.success(request, f"Content '{video.title}' has been published.")
            elif moderation_action == 'unpublish':
                # Just unpublish, don't change moderation status
                video.is_published = False
                messages.success(request, f"Content '{video.title}' has been unpublished.")
            else:
                # Update published status based on moderation status for regular save
                if moderation_status == 'approved':
                    video.is_published = True
                    video.requires_moderation = False
                elif moderation_status == 'rejected':
                    video.is_published = False
                
                if moderation_status:
                    messages.success(request, f"Content '{video.title}' moderation status updated to {moderation_status}.")
                else:
                    messages.success(request, f"Content '{video.title}' has been updated.")
            
            # Ensure moderation_status is never NULL before saving
            if video.moderation_status is None:
                # Default to the previous status, or 'pending' if that's unavailable
                try:
                    old_video = Video.objects.get(id=video_id)
                    video.moderation_status = old_video.moderation_status
                except:
                    video.moderation_status = 'pending'
            
            video.save()
            
            # Handle creator notification if checked
            if notify_creator:
                # Use the new notifications model
                try:
                    from notifications.models import Notification
                    
                    # Create default message if none provided
                    default_message = ""
                    if video.moderation_status == 'approved':
                        default_message = f"Your content '{video.title}' has been approved by our moderation team and is now visible to the community."
                    elif video.moderation_status == 'rejected':
                        default_message = f"Your content '{video.title}' has been rejected by our moderation team for not meeting our community guidelines."
                    elif moderation_action == 'publish':
                        default_message = f"Your content '{video.title}' has been published and is now visible to the community."
                    elif moderation_action == 'unpublish':
                        default_message = f"Your content '{video.title}' has been unpublished and is no longer visible to the community."
                    
                    notification_message = creator_message if creator_message else default_message
                    
                    Notification.objects.create(
                        recipient=video.creator,  # Using creator instead of user
                        actor=request.user,
                        verb=f"Your content has been {video.moderation_status}",
                        description=notification_message,
                        content_type=ContentType.objects.get_for_model(video),
                        object_id=video.id,
                        notification_type='moderation',
                        url=f"/videos/{video.id}/"
                    )
                    messages.success(request, f"Notification sent to {video.creator.username}.")
                except Exception as e:
                    messages.error(request, f"Failed to send notification: {str(e)}")
            
            return redirect('custom_admin:content_detail', video_id=video.id)
        
        elif action == 'delete_content':
            # Delete the content
            title = video.title
            video.delete()
            messages.success(request, f"Content '{title}' deleted successfully.")
            return redirect('custom_admin:content_list')
        
        elif action == 'resolve_report':
            # Resolve a report
            report_id = request.POST.get('report_id')
            try:
                report = Report.objects.get(id=report_id)
                report.status = 'resolved'
                report.resolved_by = request.user
                report.resolved_at = timezone.now()
                report.save()
                messages.success(request, f"Report #{report_id} has been marked as resolved.")
            except Report.DoesNotExist:
                messages.error(request, f"Report #{report_id} not found.")
            return redirect('custom_admin:content_detail', video_id=video.id)
    
    # Get content statistics and related data
    # Don't import Count locally, use the global import
    # from django.db.models import Count
    
    # Get comments for this video
    comments_count = video.comments.count() if hasattr(video, 'comments') else 0
    
    # Get likes for this video
    likes_count = video.likes.count() if hasattr(video, 'likes') else 0
    
    # Get reports for this video
    reports = Report.objects.filter(
        content_type=ContentType.objects.get_for_model(Video),
        object_id=video.id
    ).order_by('-created_at')
    
    # Check if content is reported and count active reports
    is_reported = reports.filter(status__in=['pending', 'reviewed']).exists()
    report_count = reports.filter(status__in=['pending', 'reviewed']).count()
    
    context = {
        'admin_section': 'content',
        'video': video,
        'comments_count': comments_count,
        'likes_count': likes_count,
        'reports': reports,
        'is_reported': is_reported,
        'report_count': report_count,
    }
    
    return render(request, 'custom_admin/content_detail.html', context)

@login_required
def admin_list(request):
    """Display a list of admin users."""
    # Check if user has permission to manage admins
    if not request.user.is_admin or request.user.admin_role.level > 1:
        messages.error(request, "You do not have permission to manage admin users.")
        return redirect('custom_admin:dashboard')
    
    # Handle form submissions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_admin':
            user_id = request.POST.get('admin_username')
            role_level = int(request.POST.get('admin_role', 3))
            notes = request.POST.get('admin_notes', '')
            send_notification = request.POST.get('send_notification') == 'on'
            
            # Get the user and role
            try:
                user = CustomUser.objects.get(id=user_id)
                role = AdminRole.objects.get(level=role_level)
                
                # Make the user an admin
                user.is_admin = True
                user.admin_role = role
                user.save()
                
                # Create notification if requested
                if send_notification:
                    # This would typically send an email
                    # For now, just log the action
                    print(f"Notification sent to {user.username} about admin role assignment")
                
                messages.success(request, f"User {user.username} has been made a {role.name}.")
            except (CustomUser.DoesNotExist, AdminRole.DoesNotExist):
                messages.error(request, "Invalid user or role selection.")
            
            return redirect('custom_admin:admin_list')
        
        elif action == 'change_role':
            user_id = request.POST.get('admin_id')
            new_role_level = int(request.POST.get('new_role', 3))
            reason = request.POST.get('change_reason', '')
            
            # Get the user and role
            try:
                user = CustomUser.objects.get(id=user_id)
                new_role = AdminRole.objects.get(level=new_role_level)
                
                # Update the admin role
                old_role = user.admin_role
                user.admin_role = new_role
                user.save()
                
                messages.success(request, f"{user.username}'s role changed from {old_role.name} to {new_role.name}.")
            except (CustomUser.DoesNotExist, AdminRole.DoesNotExist):
                messages.error(request, "Invalid user or role selection.")
            
            return redirect('custom_admin:admin_list')
        
        elif action == 'remove_admin':
            user_id = request.POST.get('admin_id')
            reason = request.POST.get('remove_reason', '')
            
            # Get the user
            try:
                user = CustomUser.objects.get(id=user_id)
                
                # Remove admin status
                old_role = user.admin_role
                user.is_admin = False
                user.admin_role = None
                user.save()
                
                messages.success(request, f"{user.username} has been removed from the admin team.")
            except CustomUser.DoesNotExist:
                messages.error(request, "Invalid user selection.")
            
            return redirect('custom_admin:admin_list')
    
    # Get all admin users
    admins = CustomUser.objects.filter(is_admin=True)
    
    # Get non-admin users for the add admin form
    non_admins = CustomUser.objects.filter(is_admin=False)
    
    context = {
        'admin_section': 'admins',
        'admins': admins,
        'non_admins': non_admins,
    }
    
    return render(request, 'custom_admin/admin_list.html', context)

@login_required
def admin_roles(request):
    """Display and manage admin roles."""
    # Check if user has permission to manage admins
    if not request.user.is_admin or request.user.admin_role.level > 1:
        messages.error(request, "You do not have permission to manage admin roles.")
        return redirect('custom_admin:dashboard')
    
    # Handle form submissions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_role':
            role_name = request.POST.get('role_name')
            role_level = int(request.POST.get('role_level', 4))
            description = request.POST.get('role_description', '')
            
            # Check if a role with this level already exists
            if AdminRole.objects.filter(level=role_level).exists() and role_level <= 3:
                messages.error(request, f"A built-in role already exists with level {role_level}.")
            else:
                # Create the role
                role = AdminRole.objects.create(
                    name=role_name,
                    level=role_level,
                    description=description
                )
                
                # Set permissions based on checkboxes
                # This would typically save to a permissions model
                # For now, just log the action
                print(f"Role {role_name} created with level {role_level}")
                
                messages.success(request, f"Role '{role_name}' has been created.")
            
            return redirect('custom_admin:admin_roles')
        
        elif action == 'edit_role':
            role_id = request.POST.get('role_id')
            role_name = request.POST.get('role_name')
            role_level = int(request.POST.get('role_level', 4))
            description = request.POST.get('role_description', '')
            
            try:
                role = AdminRole.objects.get(id=role_id)
                
                # Check if another role with this level already exists
                if role.level != role_level and AdminRole.objects.filter(level=role_level).exists() and role_level <= 3:
                    messages.error(request, f"A built-in role already exists with level {role_level}.")
                else:
                    # Update the role
                    role.name = role_name
                    role.level = role_level
                    role.description = description
                    role.save()
                    
                    messages.success(request, f"Role '{role_name}' has been updated.")
            except AdminRole.DoesNotExist:
                messages.error(request, "Invalid role selection.")
            
            return redirect('custom_admin:admin_roles')
        
        elif action == 'delete_role':
            role_id = request.POST.get('role_id')
            reassign_role_id = request.POST.get('reassign_role')
            
            try:
                role = AdminRole.objects.get(id=role_id)
                
                # Don't allow deleting built-in roles
                if role.level <= 3:
                    messages.error(request, "Cannot delete built-in roles.")
                    return redirect('custom_admin:admin_roles')
                
                # Get users with this role
                affected_users = CustomUser.objects.filter(admin_role=role)
                
                # Reassign users if specified
                if reassign_role_id:
                    try:
                        new_role = AdminRole.objects.get(id=reassign_role_id)
                        for user in affected_users:
                            user.admin_role = new_role
                            user.save()
                    except AdminRole.DoesNotExist:
                        # Remove admin status if no valid role
                        for user in affected_users:
                            user.is_admin = False
                            user.admin_role = None
                            user.save()
                else:
                    # Remove admin status
                    for user in affected_users:
                        user.is_admin = False
                        user.admin_role = None
                        user.save()
                
                # Delete the role
                role_name = role.name
                role.delete()
                
                messages.success(request, f"Role '{role_name}' has been deleted.")
            except AdminRole.DoesNotExist:
                messages.error(request, "Invalid role selection.")
            
            return redirect('custom_admin:admin_roles')
    
    # Get all admin roles
    roles = AdminRole.objects.all().order_by('level')
    
    context = {
        'admin_section': 'admins',
        'roles': roles,
    }
    
    return render(request, 'custom_admin/admin_roles.html', context)

@login_required
def content_cleanup(request):
    """Display a page for cleaning up orphaned content."""
    # Check if user has permission to manage content
    if not request.user.is_admin or request.user.admin_role.level > 2:
        messages.error(request, "You do not have permission to access content management.")
        return redirect('custom_admin:dashboard')
    
    # Get videos without creators
    orphaned_videos = Video.objects.filter(creator__isnull=True)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        video_ids = request.POST.getlist('video_ids')
        
        if action == 'delete' and video_ids:
            # Delete selected videos
            deleted_count = Video.objects.filter(id__in=video_ids).delete()[0]
            messages.success(request, f"{deleted_count} videos successfully deleted.")
            return redirect('custom_admin:content_cleanup')
        
        elif action == 'assign' and video_ids:
            # Assign selected videos to a user
            assign_to_id = request.POST.get('assign_to')
            if assign_to_id:
                try:
                    user = CustomUser.objects.get(id=assign_to_id)
                    updated_count = Video.objects.filter(id__in=video_ids).update(creator=user)
                    messages.success(request, f"{updated_count} videos assigned to {user.username}.")
                    return redirect('custom_admin:content_cleanup')
                except CustomUser.DoesNotExist:
                    messages.error(request, "Selected user does not exist.")
            else:
                messages.error(request, "Please select a user to assign videos to.")
    
    # Get all active users for assignment dropdown
    users = CustomUser.objects.filter(is_active=True)
    
    context = {
        'admin_section': 'content',
        'orphaned_videos': orphaned_videos,
        'users': users,
    }
    
    return render(request, 'custom_admin/content_cleanup.html', context)
