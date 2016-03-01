from django import template

register = template.Library()

@register.filter
def wikipedia_link(pagetitle, langcode):
    return '<a href="https://{0}.wikipedia.org/wiki/{1}">{2}</a>'.format(langcode, pagetitle.replace(' ', '_'), pagetitle)