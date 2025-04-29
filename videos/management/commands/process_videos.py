import os
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from videos.models import Video
from videos.utils import convert_video_to_hls, check_ffmpeg

class Command(BaseCommand):
    help = 'Process videos for HLS conversion that need to be converted'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all videos, not just pending ones',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Limit the number of videos to process',
        )

    def handle(self, *args, **options):
        process_all = options['all']
        limit = options['limit']

        # Check if FFmpeg is available
        if not check_ffmpeg():
            self.stdout.write(self.style.ERROR('FFmpeg is not available. Cannot process videos.'))
            return

        # Query for videos that need processing
        if process_all:
            videos = Video.objects.filter(content_type='video').exclude(file='').order_by('-created_at')[:limit]
        else:
            # Only process videos that:
            # 1. Are video type
            # 2. Have a file
            # 3. Either don't have an HLS URL or have the same URL as their file URL (fallback)
            videos = Video.objects.filter(
                content_type='video',
            ).exclude(
                file=''
            ).filter(
                hls_url=''
            ).order_by('-created_at')[:limit]

        if not videos:
            self.stdout.write(self.style.SUCCESS('No videos need processing'))
            return

        self.stdout.write(self.style.SUCCESS(f'Found {videos.count()} videos to process'))

        success_count = 0
        error_count = 0

        for video in videos:
            self.stdout.write(f'Processing video ID {video.id}: {video.title}')
            
            try:
                # Get video file path
                video_path = os.path.join(settings.MEDIA_ROOT, video.file.name)
                
                # Ensure file exists
                if not os.path.exists(video_path):
                    self.stdout.write(self.style.WARNING(f'Video file not found: {video_path}'))
                    error_count += 1
                    continue

                # Convert to HLS
                start_time = time.time()
                success, result = convert_video_to_hls(video_path)
                end_time = time.time()
                
                if success:
                    # Update the video with the HLS URL
                    video.hls_url = result
                    video.save()
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully converted video ID {video.id} in {end_time - start_time:.2f} seconds'
                        )
                    )
                else:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed to convert video ID {video.id}: {result}'
                        )
                    )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Error processing video ID {video.id}: {str(e)}'
                    )
                )
                import traceback
                self.stdout.write(traceback.format_exc())
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Processing complete. {success_count} successful, {error_count} failed.'
            )
        ) 