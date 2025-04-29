from django import forms
from .models import Video, Playlist

class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['title', 'description', 'content_type', 'file', 'image', 'blog_content', 'thumbnail']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'blog_content': forms.Textarea(attrs={'rows': 10, 'class': 'blog-content-editor'}),
        }
        help_texts = {
            'title': 'Give your content a descriptive title.',
            'description': 'All uploads are subject to review by our moderation team before being published.',
        }
    
    # Add checkbox for is_published that will be managed by the view
    is_published = forms.BooleanField(
        required=False,
        label='Request publication after moderation',
        help_text='When checked, your content will be published automatically after approval.',
        initial=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields not required so we can conditionally validate them
        self.fields['file'].required = False
        self.fields['image'].required = False
        self.fields['blog_content'].required = False
        self.fields['thumbnail'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('content_type')
        file = cleaned_data.get('file')
        image = cleaned_data.get('image')
        blog_content = cleaned_data.get('blog_content')
        thumbnail = cleaned_data.get('thumbnail')
        
        # Validate based on content type
        if content_type == 'video':
            if not file:
                self.add_error('file', 'Video file is required for video content.')
            if not thumbnail:
                self.add_error('thumbnail', 'Thumbnail is recommended for video content.')
                
        elif content_type == 'photo':
            if not image:
                self.add_error('image', 'Image file is required for photo content.')
                
        elif content_type == 'blog':
            if not blog_content or not blog_content.strip():
                self.add_error('blog_content', 'Content is required for blog posts.')
            if not thumbnail:
                self.add_error('thumbnail', 'Thumbnail is required for blog content to display properly in listings.')
                
        return cleaned_data

class PlaylistForm(forms.ModelForm):
    class Meta:
        model = Playlist
        fields = ['title', 'description', 'is_public']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        } 