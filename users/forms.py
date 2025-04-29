from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
import re

# Define the non-allauth dependent form
class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'username', 'email', 'bio', 'avatar', 'website', 'show_email']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

# Then, define the allauth dependent form
from allauth.account.forms import SignupForm as AllauthSignupForm

class SignupForm(AllauthSignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if email is verified in session
        if self.request and self.request.session.get('signup_email_verified'):
            # Get the verified email
            verified_email = self.request.session.get('signup_email')
            # Set initial value and make field read-only
            self.fields['email'].initial = verified_email
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['class'] = 'form-control bg-light'
            # Add a hidden field to preserve the email value on form submission
            self.fields['email'].widget.attrs['value'] = verified_email

    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
            'autocomplete': 'email'
        })
    )
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username',
            'autocomplete': 'username'
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a password',
            'autocomplete': 'new-password'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Basic email format validation
            email_validator = EmailValidator()
            try:
                email_validator(email)
            except ValidationError:
                raise forms.ValidationError('Please enter a valid email address.')

            # Check for disposable email domains (you can expand this list)
            disposable_domains = ['tempmail.com', 'throwawaymail.com']
            domain = email.split('@')[1].lower()
            if domain in disposable_domains:
                raise forms.ValidationError('Please use a permanent email address.')

            # If email is verified in session, ensure it matches
            if self.request and self.request.session.get('signup_email_verified'):
                verified_email = self.request.session.get('signup_email')
                if email != verified_email:
                    raise forms.ValidationError('Email cannot be changed after verification.')

        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Username format validation
            if not re.match(r'^[\w.@+-]+$', username):
                raise forms.ValidationError('Username can only contain letters, numbers, and @/./+/-/_ characters.')
            
            # Username length validation
            if len(username) < 3:
                raise forms.ValidationError('Username must be at least 3 characters long.')
            if len(username) > 30:
                raise forms.ValidationError('Username cannot be longer than 30 characters.')

        return username

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            # Password strength validation
            if len(password) < 8:
                raise forms.ValidationError('Password must be at least 8 characters long.')
            if not re.search(r'[A-Z]', password):
                raise forms.ValidationError('Password must contain at least one uppercase letter.')
            if not re.search(r'[a-z]', password):
                raise forms.ValidationError('Password must contain at least one lowercase letter.')
            if not re.search(r'[0-9]', password):
                raise forms.ValidationError('Password must contain at least one number.')
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                raise forms.ValidationError('Password must contain at least one special character.')

        return password

    def save(self, request):
        user = super().save(request)
        # Additional user setup if needed
        return user 