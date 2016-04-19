from django import template
from django.utils.html import format_html

register = template.Library()

@register.filter
def wikipedia_link(pagetitle, langcode, page_id):
    if page_id == 0:
        return format_html('<a class="new" href="https://{}.wikipedia.org/wiki/{}">{}</a>', langcode, pagetitle.replace(' ', '_'), pagetitle)
    else:
        return format_html('<a href="https://{}.wikipedia.org/wiki/{}">{}</a>', langcode, pagetitle.replace(' ', '_'), pagetitle)