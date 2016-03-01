from django import template

register = template.Library()

register.filter('wikipedia_link', wikipedia_link)

def wikipedia_link(pagetitle, langcode):
    return '<a href="https://{0}.wikipedia.org/wiki/{1}">{2}</a>'.format(langcode, pagetitle.replace(' ', '_'), pagetitle)