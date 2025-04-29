from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.template import TemplateDoesNotExist

class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom adapter for django-allauth to handle redirects for signup verification"""
    
    def get_signup_redirect_url(self, request):
        """
        Override the signup redirect URL after successful signup
        """
        # After successful signup, always redirect to the home page
        return settings.LOGIN_REDIRECT_URL
    
    def get_login_redirect_url(self, request):
        """Normal login redirect behavior"""
        return settings.LOGIN_REDIRECT_URL
        
    def render_mail(self, template_prefix, email, context):
        """
        Renders e-mail templates
        """
        # For our custom verification emails, use our custom template
        if template_prefix == 'account/email/email_confirmation':
            try:
                subject = 'Verify your email address'
                message = render_to_string('users/emails/email_confirmation.html', context)
                send_mail(
                    subject,
                    '',  # Plain text version (not used)
                    None,  # From Email (uses DEFAULT_FROM_EMAIL)
                    [email],
                    html_message=message,
                    fail_silently=False,
                )
                # Return a dummy message object to satisfy allauth
                from django.core.mail import EmailMessage
                return EmailMessage(subject, message, to=[email])
            except TemplateDoesNotExist:
                # Fall back to allauth's default template if our custom one doesn't exist
                return super().render_mail(template_prefix, email, context)
            
        # For all other emails, use allauth's default handling
        return super().render_mail(template_prefix, email, context)
        
    def is_open_for_signup(self, request):
        # Always allow signup
        return True
        
    def save_user(self, request, user, form, commit=True):
        """
        This is called when saving user via allauth registration.
        We use this to set up the email field from the session.
        """
        # Use our verified email from session
        if request.session.get('signup_email_verified'):
            user.email = request.session.get('signup_email')
            # Mark the user as active since email is verified
            user.is_active = True
            
            # Clear verification data from session
            if 'signup_email' in request.session:
                del request.session['signup_email']
            if 'signup_email_otp' in request.session:
                del request.session['signup_email_otp']
            if 'signup_email_verified' in request.session:
                del request.session['signup_email_verified']
                
        return super().save_user(request, user, form, commit)
        
    def populate_username(self, request, user):
        """Populate username from session or form"""
        if user.username:
            return
        
        # If we have a pre-verified email, use it to generate a username
        if request.session.get('signup_email_verified'):
            user.username = self.generate_unique_username([
                request.session.get('signup_email').split('@')[0],
                'user'
            ])
        else:
            # Use default allauth behavior
            super().populate_username(request, user) 