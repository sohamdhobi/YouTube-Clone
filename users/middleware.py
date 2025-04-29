from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.urls.exceptions import Resolver404
from django.urls import resolve
from django.http import HttpResponseRedirect

class AdminPermissionMiddleware:
    """
    Middleware to check if users have the required admin permissions to access specific admin areas.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the current user
        user = request.user

        # Check if we're in an admin area
        try:
            resolver_match = resolve(request.path)
            namespace = resolver_match.namespace
            view_name = resolver_match.url_name
            
            # If this is an admin view (custom admin, not Django admin)
            if namespace == 'custom_admin':
                # Only logged in and admin users can access
                if not user.is_authenticated:
                    messages.error(request, _('You must be logged in to access the admin area.'))
                    return redirect(reverse('account_login') + f'?next={request.path}')
                    
                if not user.is_admin:
                    messages.error(request, _('You do not have permission to access the admin area.'))
                    return redirect('core:index')
                
                # Check for specific permissions based on view
                if view_name.startswith('user_') and not user.has_admin_permission('can_manage_users'):
                    messages.error(request, _('You do not have permission to manage users.'))
                    return redirect(reverse('custom_admin:dashboard'))
                    
                if view_name.startswith('content_') and not user.has_admin_permission('can_manage_content'):
                    messages.error(request, _('You do not have permission to manage content.'))
                    return redirect(reverse('custom_admin:dashboard'))
                    
                if view_name.startswith('setting_') and not user.has_admin_permission('can_manage_settings'):
                    messages.error(request, _('You do not have permission to manage settings.'))
                    return redirect(reverse('custom_admin:dashboard'))
                    
                if view_name.startswith('admin_') and not user.has_admin_permission('can_manage_admins'):
                    messages.error(request, _('You do not have permission to manage admins.'))
                    return redirect(reverse('custom_admin:dashboard'))
        except Resolver404:
            # Not a registered URL pattern
            pass

        # If all checks pass or not an admin area, continue with the request
        response = self.get_response(request)
        return response 

class EmailVerificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List of URLs that don't require email verification
        exempt_urls = [
            'account_login',
            'account_logout',
            'account_signup',
            'users:pre_signup_email_verification',
            'users:verify_signup_email',
            'password_reset_request',
            'password_reset_verify_otp',
            'password_reset_confirm',
            'password_reset_from_admin',
            'admin_password_reset',
        ]

        # Check if user is authenticated but email is not verified
        if request.user.is_authenticated and not request.user.is_active:
            # Get the current URL name
            current_url = request.resolver_match.url_name if request.resolver_match else None
            
            # If current URL is not in exempt list, redirect to email verification
            if current_url not in exempt_urls:
                messages.warning(request, 'Please verify your email to access this feature.')
                return redirect('users:pre_signup_email_verification')

        response = self.get_response(request)
        return response 

class SignupRedirectMiddleware:
    """
    Middleware that redirects users to email verification flow if needed
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # If signup form was submitted but needs email verification
        if request.method == 'POST' and request.path == reverse('account_signup') and request.session.get('needs_email_verification'):
            # Clear the flag
            del request.session['needs_email_verification']
            # Redirect to verification
            return HttpResponseRedirect(reverse('users:pre_signup_email_verification'))
            
        return response 