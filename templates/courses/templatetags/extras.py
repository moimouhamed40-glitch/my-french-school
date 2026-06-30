# apps/courses/templatetags/extras.py
from django import template

register = template.Library()

@register.filter
def embed_url(value):
    if not value:
        return value
    video_id = None
    if 'watch?v=' in value:
        video_id = value.split('v=')[1].split('&')[0]
    elif 'youtu.be/' in value:
        video_id = value.split('youtu.be/')[1].split('?')[0]
    elif 'youtube.com/embed/' in value:
        return value
    if video_id:
        return f'https://www.youtube.com/embed/{video_id}'
    return value