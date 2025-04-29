from django.urls import path
from . import views

# Add back the app_name setting
app_name = 'custom_admin'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # User Management
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/toggle-active/', views.toggle_user_active, name='toggle_user_active'),
    path('users/send-email/', views.send_email_to_users, name='send_email_to_users'),
    
    # Content Management
    path('content/', views.content_list, name='content_list'),
    path('content/cleanup/', views.content_cleanup, name='content_cleanup'),
    path('content/<int:video_id>/', views.content_detail, name='content_detail'),
    
    # Admin Management
    path('admins/', views.admin_list, name='admin_list'),
    path('admins/roles/', views.admin_roles, name='admin_roles'),
]
