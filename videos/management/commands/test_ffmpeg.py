import os
import subprocess
import sys
from django.core.management.base import BaseCommand
from videos.utils import check_ffmpeg, FFMPEG_PATH

class Command(BaseCommand):
    help = 'Test FFmpeg detection and run a simple command'
    
    def handle(self, *args, **options):
        self.stdout.write("Testing FFmpeg detection...")
        
        # Check current directory for ffmpeg.exe
        current_dir = os.getcwd()
        ffmpeg_current = os.path.join(current_dir, 'ffmpeg.exe')
        if os.path.exists(ffmpeg_current):
            self.stdout.write(self.style.SUCCESS(f"Found FFmpeg in current directory: {ffmpeg_current}"))
            try:
                result = subprocess.run([ffmpeg_current, '-version'], 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE, 
                                        text=True)
                if result.returncode == 0:
                    self.stdout.write(self.style.SUCCESS("FFmpeg in current directory is working!"))
                    self.stdout.write(f"Version: {result.stdout.split('\n')[0]}")
                    self.stdout.write(self.style.SUCCESS(f"\nYou can set this path with:"))
                    self.stdout.write(f"python manage.py set_ffmpeg_path \"{ffmpeg_current}\"")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error testing FFmpeg in current directory: {str(e)}"))
        
        # Print PATH for debugging
        self.stdout.write("\nChecking PATH environment variable:")
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        for i, path_dir in enumerate(path_dirs):
            self.stdout.write(f"  {i+1}. {path_dir}")
        
        # Try the util function
        if check_ffmpeg():
            self.stdout.write(self.style.SUCCESS(f"\nFFmpeg found at: {FFMPEG_PATH}"))
            
            try:
                result = subprocess.run([FFMPEG_PATH, '-version'], 
                                       stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE, 
                                       text=True, 
                                       check=True)
                
                version_info = result.stdout.split('\n')[0]
                self.stdout.write(self.style.SUCCESS(f"FFmpeg version info: {version_info}"))
                
                # Test if we can run a simple command
                self.stdout.write("Testing a simple FFmpeg command...")
                
                # Create a test output directory
                test_dir = os.path.join('media', 'test_ffmpeg')
                os.makedirs(test_dir, exist_ok=True)
                
                # Create a simple text file to test FFmpeg
                test_file = os.path.join(test_dir, 'test.txt')
                with open(test_file, 'w') as f:
                    f.write("FFmpeg test file")
                
                # Try to run a simple FFmpeg command (just print file info)
                result = subprocess.run([FFMPEG_PATH, '-i', test_file], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE, 
                                      text=True)
                
                # FFmpeg typically outputs info to stderr for -i
                self.stdout.write(self.style.SUCCESS(f"FFmpeg executed successfully!"))
                self.stdout.write("Output: " + result.stderr)
                
                return
                
            except subprocess.CalledProcessError as e:
                self.stderr.write(self.style.ERROR(f"Error running FFmpeg: {str(e)}"))
                self.stderr.write(self.style.ERROR(f"Output: {e.stdout}"))
                self.stderr.write(self.style.ERROR(f"Error: {e.stderr}"))
                
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Unexpected error: {str(e)}"))
        else:
            self.stderr.write(self.style.ERROR("\nFFmpeg not found by the check_ffmpeg() function."))
            self.stderr.write(self.style.ERROR("You can set the path manually with: python manage.py set_ffmpeg_path <path>"))
            
            # Print some helpful installation instructions
            self.stdout.write("\nTo install FFmpeg:")
            self.stdout.write("1. Download from https://ffmpeg.org/download.html")
            self.stdout.write("2. Extract it to a directory (e.g., C:\\ffmpeg)")
            self.stdout.write("3. Add the bin directory to your PATH or use the set_ffmpeg_path command")
            
        # Try to call ffmpeg directly and see the error
        self.stdout.write("\nAttempting to call 'ffmpeg' directly:")
        try:
            subprocess.run(['ffmpeg', '-version'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE, 
                          text=True)
            self.stdout.write(self.style.SUCCESS("Direct call succeeded!"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error with direct call: {str(e)}")) 