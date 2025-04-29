from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('categories/', views.category_list, name='category_list'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('search/', views.search, name='search'),
    
    # Post URLs
    path('post/create/', views.create_post, name='create_post'),
    path('post/<slug:slug>/', views.post_detail, name='post_detail'),
    path('post/<slug:slug>/like/', views.like_post, name='like_post'),
    
    # Blog URLs
    path('blog/create/', views.create_blog, name='create_blog'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('blog/<slug:slug>/like/', views.like_blog, name='like_blog'),
    
    # Comment URLs
    path('comment/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    
    # Subscribed Channels
    path('subscribed/', views.subscribed_channels, name='subscribed_channels'),
    
    # Add report URL
    path('report/<str:content_type>/<int:object_id>/', views.report_content, name='report_content'),
] 