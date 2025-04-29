import os

# Make sure the directory exists
os.makedirs('custom_admin', exist_ok=True)

# Content to write
content = '''from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # User Management
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    
    # Content Management
    path('content/', views.content_list, name='content_list'),
    path('content/<int:video_id>/', views.content_detail, name='content_detail'),
    
    # Admin Management
    path('admins/', views.admin_list, name='admin_list'),
    path('admins/roles/', views.admin_roles, name='admin_roles'),
]
'''

# Write the file
with open('custom_admin/urls.py', 'w') as f:
    f.write(content)

print("File created successfully!") 