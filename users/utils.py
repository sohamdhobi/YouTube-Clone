from PIL import Image, ImageDraw, ImageFont
import random
import io
from django.core.files.base import ContentFile
from django.conf import settings
import os

def generate_avatar(user):
    """
    Generate an avatar with user's initials and random background color.
    Returns a ContentFile containing the avatar image.
    """
    # Get user's initials
    initials = ''.join(name[0].upper() for name in user.get_full_name().split() if name)
    if not initials:
        initials = user.username[:2].upper()

    # Generate random background color (avoiding white)
    while True:
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        if r + g + b > 100:  # Ensure color is not too dark
            break

    # Create a much larger image first for higher DPI
    large_size = (200, 200)  # Create 200x200 image for higher quality
    image = Image.new('RGB', large_size, (r, g, b))
    draw = ImageDraw.Draw(image)

    # Try to load Times New Roman Bold font, fallback to default if not available
    try:
        font_size = 80  # Increased font size for higher DPI
        # Try different Times New Roman Bold variants
        times_fonts = [
            os.path.join(settings.STATIC_ROOT, 'fonts', 'TimesNewRoman-Bold.ttf'),
            os.path.join(settings.STATIC_ROOT, 'fonts', 'Times New Roman Bold.ttf'),
            os.path.join(settings.STATIC_ROOT, 'fonts', 'timesbd.ttf'),
        ]
        font = None
        for font_path in times_fonts:
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except:
                continue
        if font is None:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    # Get text size
    text_bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Calculate position to center the text and remove top padding
    x = (large_size[0] - text_width) / 2
    y = (large_size[1] - text_height) / 2 - 15  # Move text up by 3 pixels

    # Draw the text once with normal density
    draw.text((x, y), initials, font=font, fill='white')

    # Resize to final size (100x100) with high quality settings
    image = image.resize((100, 100), Image.Resampling.LANCZOS)

    # Convert the image to bytes with high quality settings
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', quality=100, optimize=False)
    buffer.seek(0)

    # Create a ContentFile
    return ContentFile(buffer.getvalue(), name=f'avatar_{user.username}.png') 