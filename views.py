import gettext
from django.shortcuts import render

# Views! Views! Views, views, views, views, views views views views views views has a has a has a has a kind of mystery

LOCALEDIR = '/var/www/django-src/requestoid/requestoid/locale'

def interface_messages(langcode):
    '''
    Provides a dictionary to feed into the context, with an ISO 639-1 or -2 language code as input.
    '''

    LANGUAGE = langcode


    translation = gettext.translation('interface', localedir=LOCALEDIR, languages=[langcode])
    _ = translation.gettext

    output = {
                'brand': _('Wikipedia Requests'),
                'login_via_wikipedia': _('Login via Wikipedia'),
                'search': _('Search'),
                'add': _('Add'),
                'help': _('Help'),
                'about': _('About')
             }

    return output



def select_language(request):  # /requests
    available = [
                    {'code': 'en', 'label': 'English'}
                ]

    context = {
                  'interface': interface_messages('en'),
                  'language': 'en',
                  'available': available
              }

    return render(request, 'requestoid/select_language.html', context = context)


def homepage(request, langcode):  # /requests/en

    intro = ('The Wikipedia Requests system is a new tool to centralize '
             'the various lists of requests around Wikipedia, including '
             'lists of missing articles and requests to improve existing'
             ' articles. Requests are tagged by category and WikiProject,'
             ' making it easier to find requests based on what your interests '
             'are. We just started work on this, so check back later!')

    translation = gettext.translation('homepage', localedir=LOCALEDIR, languages=[langcode])
    _ = translation.getttext

    content = {
                  'headline': _('Help fill in the gaps on Wikipedia'),
                  'intro': _(intro)
              }

    context = {
                  'interface': interface_messages(langcode),
                  'content': content
              }

    return render(request, 'requestoid/homepage.html', context = context)