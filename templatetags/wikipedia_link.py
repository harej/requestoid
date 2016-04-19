from django import template
from django.utils.html import format_html

register = template.Library()

@register.filter
def wikipedia_link(pagetitle, langcode):
    return format_html('<a href="https://{}.wikipedia.org/wiki/{}">{}</a>', langcode, pagetitle.replace(' ', '_'), pagetitle)

@register.filter
def wikipedia_red_link(pagetitle, langcode):
    return format_html('<a class="new" href="https://{}.wikipedia.org/wiki/{}">{}</a>', langcode, pagetitle.replace(' ', '_'), pagetitle)