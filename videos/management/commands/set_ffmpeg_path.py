import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Set the path to the FFmpeg executable'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            type=str,
            help='Full path to the FFmpeg executable (e.g., C:\\ffmpeg\\bin\\ffmpeg.exe)',
        )
    
    def handle(self, *args, **options):
        path = options['path']
        
        # Check if the path exists
        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f'Error: The file {path} does not exist.'))
            return
        
        # Try to execute FFmpeg
        import subprocess
        try:
            result = subprocess.run([path, '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                self.stderr.write(self.style.ERROR(f'Error: Failed to execute {path}.'))
                self.stderr.write(self.style.ERROR(f'Error message: {result.stderr}'))
                return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: Failed to execute {path}.'))
            self.stderr.write(self.style.ERROR(f'Error message: {str(e)}'))
            return
        
        # FFmpeg is working, save the path
        config_dir = os.path.join(settings.BASE_DIR, 'videos', 'config')
        os.makedirs(config_dir, exist_ok=True)
        
        config_path = os.path.join(config_dir, 'ffmpeg_config.json')
        config = {'ffmpeg_path': path}
        
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        self.stdout.write(self.style.SUCCESS(f'FFmpeg path set to: {path}'))
        self.stdout.write(self.style.SUCCESS(f'Configuration saved to: {config_path}'))
        
        # Print FFmpeg version for confirmation
        version_line = result.stdout.strip().split('\n')[0] if result.stdout else 'Unknown version'
        self.stdout.write(self.style.SUCCESS(f'FFmpeg version: {version_line}')) 