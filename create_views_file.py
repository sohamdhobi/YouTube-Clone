import os

# Content to write
content = '''from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from users.models import CustomUser, AdminRole
from videos.models import Video

@login_required
def dashboard(request):
    if not request.user.is_admin:
        messages.error(request, 'You do not have permission to access the admin area')
        return redirect('core:home')
    
    # Dashboard stats
    total_users = CustomUser.objects.count()
    total_videos = Video.objects.count()
    
    context = {
        'total_users': total_users,
        'total_videos': total_videos,
    }
    return render(request, 'custom_admin/dashboard.html', context)

@login_required
def user_list(request):
    if not request.user.is_admin or not request.user.has_admin_permission('can_manage_users'):
        messages.error(request, 'You do not have permission to manage users')
        return redirect('custom_admin:dashboard')
    
    users = CustomUser.objects.all()
    return render(request, 'custom_admin/user_list.html', {'users': users})

@login_required
def user_detail(request, user_id):
    if not request.user.is_admin or not request.user.has_admin_permission('can_manage_users'):
        messages.error(request, 'You do not have permission to manage users')
        return redirect('custom_admin:dashboard')
    
    user = get_object_or_404(CustomUser, id=user_id)
    return render(request, 'custom_admin/user_detail.html', {'user': user})

@login_required
def content_list(request):
    if not request.user.is_admin or not request.user.has_admin_permission('can_manage_content'):
        messages.error(request, 'You do not have permission to manage content')
        return redirect('custom_admin:dashboard')
    
    videos = Video.objects.all()
    return render(request, 'custom_admin/content_list.html', {'videos': videos})

@login_required
def content_detail(request, video_id):
    if not request.user.is_admin or not request.user.has_admin_permission('can_manage_content'):
        messages.error(request, 'You do not have permission to manage content')
        return redirect('custom_admin:dashboard')
    
    video = get_object_or_404(Video, id=video_id)
    return render(request, 'custom_admin/content_detail.html', {'video': video})

@login_required
def admin_list(request):
    if not request.user.is_admin or not request.user.has_admin_permission('can_manage_admins'):
        messages.error(request, 'You do not have permission to manage admins')
        return redirect('custom_admin:dashboard')
    
    admins = CustomUser.objects.filter(is_admin=True)
    return render(request, 'custom_admin/admin_list.html', {'admins': admins})

@login_required
def admin_roles(request):
    if not request.user.is_admin or not request.user.has_admin_permission('can_manage_admins'):
        messages.error(request, 'You do not have permission to manage admin roles')
        return redirect('custom_admin:dashboard')
    
    roles = AdminRole.objects.all()
    return render(request, 'custom_admin/admin_roles.html', {'roles': roles})
'''

# Make sure the directory exists
os.makedirs('custom_admin', exist_ok=True)

# Write the file
with open('custom_admin/views.py', 'w') as f:
    f.write(content)

print("views.py file created successfully!") 