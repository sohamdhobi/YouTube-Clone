from django import forms
from .models import Post, Blog, Comment, Report
from django.core.exceptions import ValidationError

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
        }

class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['title', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Write your comment here...',
                'class': 'form-control'
            })
        }
        labels = {
            'content': ''
        }

class ReportForm(forms.ModelForm):
    """Form for reporting content (videos, images, blogs, etc.)"""
    
    class Meta:
        model = Report
        fields = ['reason', 'details']
        widgets = {
            'details': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Please provide any additional details that would help us understand this report better.'}),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        reason = cleaned_data.get('reason')
        details = cleaned_data.get('details')
        
        # If 'other' is selected, details are required
        if reason == 'other' and not details:
            raise ValidationError({'details': 'Please provide details when selecting "Other" as the reason.'})
            
        return cleaned_data 