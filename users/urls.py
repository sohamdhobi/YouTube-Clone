from django.urls import path, include
from . import views

app_name = 'users'

urlpatterns = [
    path('accounts/', include('allauth.urls')),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('channel/<str:username>/', views.channel, name='channel'),
    path('subscribe/<str:username>/', views.subscribe, name='subscribe'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('user-profile/', views.user_profile, name='user_profile'),
    path('debug-content/', views.debug_content, name='debug_content'),
    path('password-reset/request/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/verify-otp/', views.password_reset_verify_otp, name='password_reset_verify_otp'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    path('admin/password-reset/<int:user_id>/', views.admin_password_reset, name='admin_password_reset'),
    path('password-reset/<uidb64>/<token>/', views.password_reset_from_admin, name='password_reset_from_admin'),
    path('pre-signup-email-verification/', views.pre_signup_email_verification, name='pre_signup_email_verification'),
    path('verify-signup-otp/', views.verify_signup_otp, name='verify_signup_otp'),
] 