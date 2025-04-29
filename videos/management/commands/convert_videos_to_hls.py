import os
from django.core.management.base import BaseCommand
from django.conf import settings
from videos.models import Video
from videos.utils import convert_video_to_hls, check_ffmpeg
from django.db.models import Q


class Command(BaseCommand):
    help = 'Convert existing videos to HLS format'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force conversion even if videos already have HLS URLs',
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit the number of videos to process',
        )
        
        parser.add_argument(
            '--id',
            type=int,
            help='Convert a specific video by ID',
        )
    
    def handle(self, *args, **options):
        # Check if ffmpeg is available
        if not check_ffmpeg():
            self.stderr.write(self.style.ERROR('FFmpeg is not installed or not in PATH'))
            self.stderr.write(self.style.ERROR('Please install FFmpeg to use this command'))
            return
            
        force = options['force']
        limit = options.get('limit')
        video_id = options.get('id')
        
        # Filter videos to convert
        if video_id:
            videos = Video.objects.filter(id=video_id, content_type='video')
            if not videos.exists():
                self.stderr.write(self.style.ERROR(f'No video found with ID {video_id}'))
                return
        else:
            # Get videos that need conversion
            query = Q(content_type='video', file__isnull=False)
            if not force:
                # Only get videos without an HLS URL
                query &= Q(hls_url__isnull=True) | Q(hls_url='')
                
            videos = Video.objects.filter(query)
            
            if limit:
                videos = videos[:limit]
        
        total = videos.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No videos need conversion'))
            return
            
        self.stdout.write(f'Found {total} videos to convert')
        
        # Process each video
        success_count = 0
        error_count = 0
        
        for i, video in enumerate(videos, 1):
            video_path = os.path.join(settings.MEDIA_ROOT, video.file.name)
            
            self.stdout.write(f'[{i}/{total}] Converting video: {video.title} (ID: {video.id})')
            
            if not os.path.exists(video_path):
                self.stderr.write(self.style.ERROR(f'  Error: Video file not found at {video_path}'))
                error_count += 1
                continue
                
            try:
                # Convert the video to HLS format
                success, result = convert_video_to_hls(video_path)
                
                if success:
                    # Update the video model with the HLS URL
                    video.hls_url = result
                    video.save()
                    self.stdout.write(self.style.SUCCESS(f'  Success: {result}'))
                    success_count += 1
                else:
                    self.stderr.write(self.style.ERROR(f'  Error: {result}'))
                    error_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'  Error: {str(e)}'))
                error_count += 1
        
        # Show summary
        self.stdout.write(self.style.SUCCESS(f'Conversion complete: {success_count} succeeded, {error_count} failed')) 