from django import template

register = template.Library()

@register.filter
def embed_url(value):
    """Convert YouTube URL to embed URL."""
    if not value:
        return value
    
    video_id = None
    
    # https://www.youtube.com/watch?v=abc123
    if 'watch?v=' in value:
        video_id = value.split('v=')[1].split('&')[0]
    
    # https://youtu.be/abc123
    elif 'youtu.be/' in value:
        video_id = value.split('youtu.be/')[1].split('?')[0]
    
    # https://www.youtube.com/embed/abc123 (already correct)
    elif 'youtube.com/embed/' in value:
        return value
    
    # https://youtube.com/shorts/abc123
    elif 'youtube.com/shorts/' in value:
        video_id = value.split('shorts/')[1].split('?')[0]
    
    if video_id:
        return f'https://www.youtube.com/embed/{video_id}'
    
    return value