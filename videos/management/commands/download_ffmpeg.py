import os
import sys
import zipfile
import requests
import tempfile
import platform
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.text import slugify
import time
import json

class Command(BaseCommand):
    help = 'Download FFmpeg for Windows'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force download even if FFmpeg already exists',
        )
    
    def handle(self, *args, **options):
        force = options['force']
        
        # Check if we're on Windows
        if platform.system() != 'Windows':
            self.stderr.write(self.style.ERROR(f"This command only supports Windows. You're on {platform.system()}."))
            self.stderr.write(self.style.ERROR("Please install FFmpeg manually for your platform."))
            return
        
        # Define the target directory and file paths
        ffmpeg_dir = os.path.join(settings.BASE_DIR, 'ffmpeg')
        ffmpeg_bin_dir = os.path.join(ffmpeg_dir, 'bin')
        ffmpeg_exe = os.path.join(ffmpeg_bin_dir, 'ffmpeg.exe')
        
        # Check if FFmpeg already exists
        if os.path.exists(ffmpeg_exe) and not force:
            self.stdout.write(self.style.SUCCESS(f"FFmpeg already exists at {ffmpeg_exe}"))
            self.stdout.write(self.style.SUCCESS("You can use it with the command:"))
            self.stdout.write(f"python manage.py set_ffmpeg_path {ffmpeg_exe}")
            return
        
        # Create the directory if it doesn't exist
        os.makedirs(ffmpeg_bin_dir, exist_ok=True)
        
        # URLs for FFmpeg download
        # Using the gyan.dev release which is well-maintained
        ffmpeg_url = "https://github.com/GyanD/codexffmpeg/releases/download/6.1.1/ffmpeg-6.1.1-essentials_build.zip"
        
        self.stdout.write(f"Downloading FFmpeg from {ffmpeg_url}...")
        
        try:
            # Download the zip file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                response = requests.get(ffmpeg_url, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        tmp_file.write(chunk)
                        downloaded += len(chunk)
                        percentage = int(downloaded * 100 / total_size) if total_size > 0 else 0
                        self.stdout.write(f"\rDownloading: {percentage}% ({downloaded/(1024*1024):.1f}MB / {total_size/(1024*1024):.1f}MB)", ending='')
                        sys.stdout.flush()
                
                self.stdout.write("\nDownload complete.")
                
                zip_path = tmp_file.name
            
            # Extract the zip file
            self.stdout.write(f"Extracting to {ffmpeg_dir}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get the root directory name in the zip
                root_dirs = {item.split('/')[0] for item in zip_ref.namelist() if '/' in item}
                root_dir = root_dirs.pop() if root_dirs else ''
                
                # Extract all files
                zip_ref.extractall(ffmpeg_dir)
                
                # Move files from nested directory if needed
                if root_dir:
                    extracted_dir = os.path.join(ffmpeg_dir, root_dir)
                    if os.path.exists(extracted_dir):
                        # If bin directory exists in extracted dir, use that
                        extracted_bin = os.path.join(extracted_dir, 'bin')
                        if os.path.exists(extracted_bin):
                            # Copy all files from extracted bin to our bin dir
                            import shutil
                            for item in os.listdir(extracted_bin):
                                src = os.path.join(extracted_bin, item)
                                dst = os.path.join(ffmpeg_bin_dir, item)
                                if os.path.isfile(src):
                                    shutil.copy2(src, dst)
                                else:
                                    shutil.copytree(src, dst, dirs_exist_ok=True)
            
            # Delete the temporary zip file
            os.unlink(zip_path)
            
            # Check if FFmpeg.exe exists now
            if os.path.exists(ffmpeg_exe):
                self.stdout.write(self.style.SUCCESS(f"FFmpeg successfully installed to {ffmpeg_exe}"))
                
                # Save the path to the config file
                config_dir = os.path.join(settings.BASE_DIR, 'videos', 'config')
                os.makedirs(config_dir, exist_ok=True)
                
                config_path = os.path.join(config_dir, 'ffmpeg_config.json')
                config = {'ffmpeg_path': ffmpeg_exe}
                
                with open(config_path, 'w') as f:
                    json.dump(config, f)
                
                self.stdout.write(self.style.SUCCESS(f"FFmpeg path saved to config file: {config_path}"))
                
                # Test the FFmpeg executable
                import subprocess
                try:
                    result = subprocess.run([ffmpeg_exe, '-version'], 
                                           stdout=subprocess.PIPE, 
                                           stderr=subprocess.PIPE, 
                                           text=True)
                    
                    if result.returncode == 0:
                        version = result.stdout.split('\n')[0]
                        self.stdout.write(self.style.SUCCESS(f"FFmpeg test successful: {version}"))
                    else:
                        self.stderr.write(self.style.ERROR(f"FFmpeg test failed: {result.stderr}"))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error testing FFmpeg: {str(e)}"))
            else:
                self.stderr.write(self.style.ERROR(f"FFmpeg was not found at {ffmpeg_exe} after extraction."))
                self.stderr.write(self.style.ERROR("Please check the extracted files and set the path manually."))
                
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error downloading FFmpeg: {str(e)}"))
            self.stderr.write(self.style.ERROR("Please download FFmpeg manually from https://ffmpeg.org/download.html")) 