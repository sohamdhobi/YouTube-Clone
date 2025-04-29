# HLS Streaming Guide

This document explains how HTTP Live Streaming (HLS) is implemented in the YouTube Clone project.

## What is HLS?

HTTP Live Streaming (HLS) is an adaptive streaming protocol developed by Apple that enables high-quality streaming of media content over HTTP. Key benefits include:

- **Adaptive Bitrate**: Automatically adjusts video quality based on network conditions
- **Wide Compatibility**: Works on most modern browsers and devices
- **Multiple Quality Options**: Provides different resolutions for optimal viewing
- **Lower Buffering**: Reduces buffering by switching to lower quality when network is slow

## Prerequisites

To use HLS streaming in this project, you need:

1. **FFmpeg**: A command-line tool for processing video and audio files
   - Windows: Download from https://ffmpeg.org/download.html
   - macOS: `brew install ffmpeg`
   - Ubuntu: `sudo apt-get install ffmpeg`

2. **Storage**: Sufficient disk space to store HLS segments (typically 1.5-2x the original video size)

## How HLS Works in This Project

### 1. Video Upload Process

When a user uploads a video:

1. The video is saved to the media directory
2. The `convert_video_to_hls` function in `videos/utils.py` is called
3. FFmpeg converts the video to multiple quality levels (1080p, 720p, 480p, 360p)
4. A master playlist (.m3u8) file is created that references all quality levels
5. The `hls_url` field in the Video model is updated with the URL to the master playlist

### 2. Video Playback

When a user plays a video:

1. The template checks if an HLS URL is available for the video
2. If available, the HLS URL is used as the video source with type "application/x-mpegURL"
3. Video.js automatically handles HLS playback using its built-in HLS module
4. The player adapts the quality based on network conditions

## Converting Existing Videos

To convert your existing videos to HLS format, use the included management command:

```bash
# Convert all videos that don't have an HLS URL yet
python manage.py convert_videos_to_hls

# Force conversion for all videos, even those with existing HLS URLs
python manage.py convert_videos_to_hls --force

# Convert only a specific number of videos
python manage.py convert_videos_to_hls --limit 10

# Convert a specific video by ID
python manage.py convert_videos_to_hls --id 123
```

## Manual HLS URL Setup

If you have externally hosted HLS streams, you can manually set the `hls_url` field for videos:

1. Access the Django admin interface
2. Find and edit the video
3. Set the HLS URL field to point to your .m3u8 manifest file
4. Save the video

## Troubleshooting

### FFmpeg Issues

If you encounter errors during HLS conversion:

1. Verify FFmpeg is properly installed: Run `ffmpeg -version` in your command line
2. Check file permissions on the video and output directories
3. Look at the error messages in the console or logs for specific FFmpeg errors

### Playback Issues

If videos aren't playing properly:

1. Check the browser console for errors
2. Verify the HLS URL is accessible directly in the browser
3. Ensure your web server is configured to serve .m3u8 and .ts files with correct MIME types:
   - .m3u8: application/x-mpegURL or application/vnd.apple.mpegurl
   - .ts: video/MP2T

## MIME Type Configuration

### Nginx

Add to your nginx.conf or site configuration:

```
types {
    application/vnd.apple.mpegurl m3u8;
    video/mp2t ts;
}
```

### Apache

Add to your .htaccess or httpd.conf:

```
AddType application/vnd.apple.mpegurl m3u8
AddType video/mp2t ts
```

## Further Customization

To modify HLS conversion parameters, edit the `convert_video_to_hls` function in `videos/utils.py`. You can adjust:

- Segment duration (`-hls_time`)
- Number of quality levels
- Resolution and bitrate for each quality level
- Encoding parameters 