from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from allauth.account.views import SignupView

def signup_check(request):
    """
    Check if email is verified before allowing access to signup page.
    This is called when user tries to access /accounts/signup/ directly.
    """
    # If user is already authenticated, redirect to home
    if request.user.is_authenticated:
        return redirect('/')
        
    # If this is a POST request to the signup form and email is verified
    if request.method == 'POST' and request.session.get('signup_email_verified'):
        return SignupView.as_view()(request)
        
    # For all other cases (GET request or POST without verified email),
    # redirect to email verification
    if not request.session.get('signup_email_verified'):
        messages.info(request, 'Please verify your email before signing up.')
        return redirect('users:pre_signup_email_verification')
    else:
        # Email is verified, show signup form
        return SignupView.as_view()(request)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('users/', include('users.urls')),
    path('videos/', include('videos.urls')),
    path('custom-admin/', include('custom_admin.urls')),
    path('notifications/', include('notifications.urls')),
    
    # Redirect /accounts/signup/ to our custom signup check
    path('accounts/signup/', signup_check, name='signup_check'),
    
    # Django allauth URLs
    path('accounts/', include('allauth.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
