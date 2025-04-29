import os
import subprocess
import uuid
import json
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Try to load FFmpeg path from config
FFMPEG_PATH = 'ffmpeg'  # Default value

def load_ffmpeg_config():
    """Load FFmpeg path from config file"""
    global FFMPEG_PATH
    try:
        config_path = os.path.join(settings.BASE_DIR, 'videos', 'config', 'ffmpeg_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                if 'ffmpeg_path' in config and os.path.exists(config['ffmpeg_path']):
                    FFMPEG_PATH = config['ffmpeg_path']
                    logger.info(f"Using FFmpeg from config: {FFMPEG_PATH}")
                    return True
    except Exception as e:
        logger.warning(f"Error loading FFmpeg config: {str(e)}")
    return False

# Try to load right away
if not load_ffmpeg_config():
    # Try standard locations
    std_paths = [
        os.path.join(settings.BASE_DIR, 'ffmpeg', 'bin', 'ffmpeg.exe'),
        os.path.join(settings.BASE_DIR, 'ffmpeg.exe'),
    ]
    for path in std_paths:
        if os.path.exists(path):
            FFMPEG_PATH = path
            logger.info(f"Found FFmpeg at standard location: {FFMPEG_PATH}")
            break

# Print debug info
logger.info(f"FFmpeg path set to: {FFMPEG_PATH}")
print(f"FFmpeg path set to: {FFMPEG_PATH}")  # Debug printout

def convert_video_to_hls(video_path, output_dir=None):
    """
    Convert a video file to HLS format using ffmpeg.
    
    Args:
        video_path: Path to the source video file
        output_dir: Directory to store HLS files (defaults to MEDIA_ROOT/hls/{video_id})
        
    Returns:
        tuple: (success, hls_url or error_message)
    """
    try:
        # Generate unique ID for this conversion
        video_id = str(uuid.uuid4())
        
        # Set up output directory
        if not output_dir:
            output_dir = os.path.join(settings.MEDIA_ROOT, 'hls', video_id)
        
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Define output path for the master playlist
        master_path = os.path.join(output_dir, 'master.m3u8')
        
        # Check input video bit depth and format
        probe_command = [
            FFMPEG_PATH,
            '-i', video_path,
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=pix_fmt',
            '-of', 'csv=p=0',
        ]
        
        try:
            pixel_format = subprocess.check_output(probe_command, universal_newlines=True).strip()
            logger.info(f"Detected pixel format: {pixel_format}")
            
            # Determine if it's a 10-bit video (common 10-bit formats contain "10" or "p10")
            is_10bit = '10' in pixel_format
            
            # Set profile based on bit depth
            profile = 'high10' if is_10bit else 'high'
            logger.info(f"Using profile: {profile} for {'10-bit' if is_10bit else '8-bit'} video")
        except subprocess.CalledProcessError:
            # If probe fails, default to high profile
            profile = 'high'
            logger.warning("Failed to detect video bit depth, defaulting to profile: high")
            
        # Define resolutions and bitrates
        resolutions = [
            ('1080p', '1920:1080', '5000k'),  # 1080p HD
            ('720p', '1280:720', '2800k'),    # 720p HD
            ('480p', '854:480', '1400k'),     # 480p SD
            ('360p', '640:360', '800k')       # 360p SD
        ]
        
        # Create master playlist content
        master_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
        
        success_count = 0
        error_message = ""
        
        # Process each resolution
        for name, res, bitrate in resolutions:
            output_path = os.path.join(output_dir, f'{name}.m3u8')
            
            # Build ffmpeg command for this resolution
            command = [
                FFMPEG_PATH,
                '-i', video_path,
                '-c:v', 'libx264',
                '-preset', 'medium',  # Balance between speed and quality
                '-profile:v', profile,  # Use detected profile based on bit depth
                '-level', '4.1',      # Higher level for better compatibility
                '-crf', '23',         # Constant Rate Factor for quality control
                '-c:a', 'aac',
                '-b:a', '128k',       # Audio bitrate
                '-ar', '48000',       # Audio sample rate
                '-ac', '2',           # Number of audio channels
                '-s', res,
                '-hls_time', '6',     # Shorter segments for faster startup
                '-hls_list_size', '0',
                '-hls_segment_type', 'mpegts',
                '-hls_segment_filename', os.path.join(output_dir, f'{name}_%03d.ts'),
                '-f', 'hls',
                '-y',  # Overwrite existing files
                output_path
            ]
            
            # Run ffmpeg command for this resolution
            logger.info(f"Converting video to HLS ({name}): {' '.join(command)}")
            try:
                subprocess.run(command, check=True)
                
                # Add this variant to the master playlist
                bandwidth = int(bitrate.replace('k', '')) * 1000
                width, height = res.split(':')
                master_content += f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={width}x{height}\n"
                master_content += f"{name}.m3u8\n"
                
                success_count += 1
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to convert to {name}: {str(e)}")
                error_message = str(e)
                # Continue with next resolution, don't fail the entire conversion
                continue
        
        # Check if at least one resolution was converted successfully
        if success_count > 0:
            # Write the master playlist
            with open(master_path, 'w') as f:
                f.write(master_content)
            
            # Return the URL to the master playlist
            hls_url = f'{settings.MEDIA_URL}hls/{video_id}/master.m3u8'
            return True, hls_url
        
        # If all resolutions failed, try a more compatible approach
        logger.warning("All resolutions failed to convert, trying fallback method")
        
        # Try a simpler conversion as fallback (no scaling, single output)
        fallback_path = os.path.join(output_dir, 'fallback.m3u8')
        fallback_command = [
            FFMPEG_PATH,
            '-i', video_path,
            '-c:v', 'libx264',
            '-preset', 'fast',
            # No profile specified to let FFmpeg choose
            '-crf', '25',   # Lower quality for compatibility
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '44100', # More compatible sample rate
            '-ac', '2',
            '-hls_time', '10',
            '-hls_list_size', '0',
            '-hls_segment_type', 'mpegts',
            '-hls_segment_filename', os.path.join(output_dir, 'fallback_%03d.ts'),
            '-f', 'hls',
            '-y',
            fallback_path
        ]
        
        try:
            logger.info(f"Trying fallback conversion: {' '.join(fallback_command)}")
            subprocess.run(fallback_command, check=True)
            
            # Create a simple master playlist that points to the fallback
            with open(master_path, 'w') as f:
                f.write("#EXTM3U\n#EXT-X-VERSION:3\nfallback.m3u8\n")
            
            fallback_hls_url = f'{settings.MEDIA_URL}hls/{video_id}/master.m3u8'
            logger.info(f"Fallback conversion successful: {fallback_hls_url}")
            return True, fallback_hls_url
        except subprocess.CalledProcessError as e:
            logger.error(f"Fallback conversion also failed: {str(e)}")
            return False, f"All conversion methods failed: {error_message or str(e)}"
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {str(e)}")
        return False, f"FFmpeg error: {str(e)}"
        
    except Exception as e:
        logger.error(f"Error converting video to HLS: {str(e)}")
        return False, f"Error: {str(e)}"

def check_ffmpeg():
    """Check if ffmpeg is installed and available in the system path."""
    global FFMPEG_PATH
    
    # First, try using the configured path
    if FFMPEG_PATH != 'ffmpeg':
        try:
            result = subprocess.run([FFMPEG_PATH, '-version'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, 
                                  text=True)
            if result.returncode == 0:
                logger.info(f"FFmpeg found at configured path: {FFMPEG_PATH}")
                return True
        except Exception as e:
            logger.warning(f"Error using configured FFmpeg path: {str(e)}")
    
    try:
        # Try the standard approach
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        FFMPEG_PATH = 'ffmpeg'
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        # On Windows, try common installation locations
        import platform
        if platform.system() == 'Windows':
            # Check common Windows FFmpeg installation paths
            common_paths = [
                'C:\\ffmpeg\\bin\\ffmpeg.exe',
                'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
                'C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe',
                os.path.join(os.environ.get('USERPROFILE', ''), 'ffmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ffmpeg', 'bin', 'ffmpeg.exe'),
                # Check the root directory of the application
                os.path.join(settings.BASE_DIR, 'ffmpeg.exe'),
                os.path.join(settings.BASE_DIR, 'ffmpeg', 'bin', 'ffmpeg.exe'),
                # Additional paths
                'C:\\Users\\soham dhobi\\Desktop\\ffmpeg\\bin\\ffmpeg.exe',
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    try:
                        subprocess.run([path, '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        FFMPEG_PATH = path
                        logger.info(f"Found FFmpeg at: {FFMPEG_PATH}")
                        
                        # Save the path to config for future use
                        try:
                            config_dir = os.path.join(settings.BASE_DIR, 'videos', 'config')
                            os.makedirs(config_dir, exist_ok=True)
                            
                            config_path = os.path.join(config_dir, 'ffmpeg_config.json')
                            config = {'ffmpeg_path': path}
                            
                            with open(config_path, 'w') as f:
                                json.dump(config, f)
                            
                            logger.info(f"Saved FFmpeg path to config: {config_path}")
                        except Exception as e:
                            logger.warning(f"Could not save FFmpeg path to config: {str(e)}")
                            
                        return True
                    except (subprocess.SubprocessError, FileNotFoundError):
                        continue
                        
        logger.error("FFmpeg not found. Please configure the path using 'python manage.py set_ffmpeg_path'.")
        return False 