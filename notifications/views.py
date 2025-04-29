from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic import ListView, View, DetailView
from django.contrib import messages
from .models import Notification
from videos.models import Video
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

# Create your views here.

@method_decorator(login_required, name='dispatch')
class NotificationListView(ListView):
    """View for listing user notifications"""
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 15
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

@method_decorator(login_required, name='dispatch')
class NotificationDetailView(DetailView):
    """View for detailed notification information with action options"""
    model = Notification
    template_name = 'notifications/notification_detail.html'
    context_object_name = 'notification'
    pk_url_kwarg = 'notification_id'
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notification = self.object
        
        # Mark the notification as read when viewed
        if notification.unread:
            notification.mark_as_read()
        
        # Get the related content object if it exists
        if notification.content_type and notification.object_id:
            content_object = notification.content_object
            context['content_object'] = content_object
            
            # Add specific context for moderation notifications
            if notification.notification_type == 'moderation' and isinstance(content_object, Video):
                context['moderation_status'] = content_object.moderation_status
                context['moderation_notes'] = content_object.moderation_notes
                context['moderated_by'] = content_object.moderated_by
                context['moderated_at'] = content_object.moderated_at
                context['is_published'] = content_object.is_published
        
        return context
    
    def post(self, request, *args, **kwargs):
        notification = self.get_object()
        content_object = notification.content_object
        
        if not content_object or not isinstance(content_object, Video):
            messages.error(request, "Unable to perform this action on the content.")
            return redirect('notifications:detail', notification_id=notification.id)
        
        action = request.POST.get('action')
        
        if action == 'edit_content':
            # Redirect to edit page
            return redirect('videos:edit', slug=content_object.slug)
            
        elif action == 'delete_content':
            # Delete the content
            if content_object.creator != request.user:
                messages.error(request, "You don't have permission to delete this content.")
                return redirect('notifications:detail', notification_id=notification.id)
            
            content_object.delete()
            messages.success(request, "Content successfully deleted.")
            return redirect('notifications:list')
            
        elif action == 'request_review':
            # Process appeal or review request for any content status
            review_message = request.POST.get('review_message', '').strip()
            
            if not review_message:
                messages.error(request, "Please provide a message explaining your request.")
                return redirect('notifications:detail', notification_id=notification.id)
            
            # Get the current status for the message
            current_status = content_object.moderation_status
            
            # Update the content status based on current status
            if current_status == 'rejected':
                # For rejected content, set back to pending
                content_object.moderation_status = 'pending'
                content_object.requires_moderation = True
                status_msg = "Your content has been submitted for review."
            elif current_status == 'approved':
                # For approved content, keep the status but add notes
                status_msg = "Your feedback has been submitted to our moderation team."
            else:  # pending
                # For pending content, keep the status but add notes
                status_msg = "Your additional information has been sent to our moderation team."
            
            # Add the appeal message to moderation notes with formatting
            from django.utils import timezone
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
            
            # Add user appeal to moderation notes
            content_object.moderation_notes = (
                f"{content_object.moderation_notes or ''}\n\n"
                f"=== USER APPEAL ({timestamp}) ===\n"
                f"{review_message}"
            )
            content_object.save()
            
            # Create a notification for admins (placeholder - would need admin notification logic)
            # In a real implementation, you'd create a notification for admin/moderators here
            try:
                from core.models import AdminLog
                from django.contrib.contenttypes.models import ContentType
                
                # Log the appeal for admin records
                AdminLog.objects.create(
                    admin=None,  # No admin for user-initiated action
                    action_type="review_request",
                    description=f"User {request.user.username} has submitted an appeal/request for content ID {content_object.id}: {review_message[:100]}{'...' if len(review_message) > 100 else ''}",
                    content_type=ContentType.objects.get_for_model(content_object),
                    object_id=content_object.id,
                    target_user=request.user
                )
            except Exception as e:
                print(f"Failed to create admin log: {str(e)}")
                
            messages.success(request, status_msg)
            return redirect('notifications:detail', notification_id=notification.id)
            
        elif action == 'publish_content':
            # Publish approved content
            if content_object.moderation_status != 'approved':
                messages.error(request, "You can only publish content that has been approved.")
                return redirect('notifications:detail', notification_id=notification.id)
            
            content_object.is_published = True
            content_object.save()
            
            messages.success(request, "Your content has been published.")
            return redirect('notifications:detail', notification_id=notification.id)
        
        messages.error(request, "Invalid action.")
        return redirect('notifications:detail', notification_id=notification.id)

@login_required
def mark_as_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.mark_as_read()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    # Redirect to the detailed notification view instead of the URL
    return redirect('notifications:detail', notification_id=notification.id)

@login_required
def mark_all_as_read(request):
    """Mark all notifications as read"""
    notifications = Notification.objects.filter(recipient=request.user, unread=True)
    for notification in notifications:
        notification.mark_as_read()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('notifications:list')
