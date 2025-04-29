from django.urls import path
from . import views

app_name = 'videos'

urlpatterns = [
    path('upload/', views.video_upload, name='upload'),
    path('watch/<slug:slug>/', views.video_detail, name='watch'),
    path('edit/<slug:slug>/', views.video_edit, name='edit'),
    path('delete/<slug:slug>/', views.video_delete, name='delete'),
    path('toggle-privacy/<slug:slug>/', views.toggle_privacy, name='toggle_privacy'),
    path('like/<slug:slug>/', views.video_like, name='like'),
    path('comment/<slug:slug>/', views.comment_video, name='comment'),
    path('comment/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    path('comment/<int:comment_id>/edit/', views.edit_comment, name='edit_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path('playlist/create/', views.playlist_create, name='playlist_create'),
    path('playlist/<int:pk>/', views.playlist_detail, name='playlist_detail'),
    path('playlist/<int:pk>/edit/', views.playlist_edit, name='playlist_edit'),
    path('playlist/<int:pk>/delete/', views.playlist_delete, name='playlist_delete'),
    path('playlist/<int:pk>/player/', views.playlist_player, name='playlist_player'),
    path('playlist/<int:pk>/reorder/', views.playlist_reorder, name='playlist_reorder'),
    path('playlist/<int:pk>/add/<slug:video_slug>/', views.playlist_add_item, name='playlist_add_item'),
    path('playlist/<int:pk>/remove/<int:video_pk>/', views.playlist_remove_item, name='playlist_remove_item'),
    path('add-to-playlist/<slug:video_slug>/', views.add_to_playlist, name='add_to_playlist'),
    path('browse/', views.browse, name='browse'),
    path('fix-missing-slugs/', views.fix_missing_slugs, name='fix_missing_slugs'),
    path('update-watch-time/', views.update_watch_time, name='update_watch_time'),
] 