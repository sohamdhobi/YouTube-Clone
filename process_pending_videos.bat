@echo off
cd /d "%~dp0"
echo Processing pending videos at %date% %time%
python manage.py process_videos >> logs/video_processing.log 2>&1
echo Completed at %date% %time% 