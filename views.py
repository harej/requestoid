import configparser
import gettext
import os
from django.shortcuts import render
from django.http.response import HttpResponseRedirect
from mwoauth import ConsumerToken, Handshaker, tokens

# Views! Views! Views, views, views, views, views views views views views views has a has a has a has a kind of mystery

ROOTDIR = '/var/www/django-src/requestoid/requestoid'
LOCALEDIR = ROOTDIR + '/locale'


def requests_handshaker():
    keyfile = configparser.ConfigParser()
    keyfile.read([os.path.expanduser(ROOTDIR + '/.oauth.ini')])
    consumer_key = keyfile.get('oauth', 'consumer_key')
    consumer_secret = keyfile.get('oauth', 'consumer_secret')
    consumer_token = ConsumerToken(consumer_key, consumer_secret)
    return Handshaker("https://meta.wikimedia.org/w/index.php", consumer_token)


def get_username(request):
    handshaker = requests_handshaker()
    if 'access' in request.COOKIES:
        access_token = request.session['access_token']
        return handshaker.identify(access_token)
    else:
        return None


def interface_messages(request, langcode):
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

    username = get_username(request)
    if username != None:
        output['username'] = username  # leave 'username' key unset if no session

    return output


###

def select_language(request):  # /requests
    available = [
                    {'code': 'en', 'label': 'English'}
                ]

    context = {
                  'interface': interface_messages(request, 'en'),
                  'language': 'en',
                  'available': available
              }

    return render(request, 'requestoid/select_language.html', context = context)


def homepage(request, langcode):  # /requests/en

    translation = gettext.translation('homepage', localedir=LOCALEDIR, languages=[langcode])
    _ = translation.gettext

    content = {
                  'headline': _('Help fill in the gaps on Wikipedia'),
                  'intro': _('The Wikipedia Requests system is a new tool to centralize the various lists of requests around Wikipedia, including lists of missing articles and requests to improve existing articles. Requests are tagged by category and WikiProject, making it easier to find requests based on what your interests are. We just started work on this, so check back later!')
              }

    context = {
                  'interface': interface_messages(request, langcode),
                  'language': langcode,
                  'content': content
              }

    return render(request, 'requestoid/homepage.html', context = context)


def auth(request, langcode):  # /requests/en/auth
    handshaker = requests_handshaker()
    redirect, request_token = handshaker.initiate()
    request.session['request_token_key'] = request_token.key.decode('utf-8')
    request.session['request_token_secret'] = request_token.secret.decode('utf-8')
    request.session['langcode'] = str(langcode)
    return HttpResponseRedirect(redirect)  # This hands the user off to Wikimedia; user returns to the website via the callback view which implements the session


def callback(request):  # /requests/callback
    oauth_verifier = request.GET['oauth_verifier']
    oauth_token = request.GET['oauth_token']
    handshaker = requests_handshaker()
    request_key = request.session['request_token_key'].encode('utf-8')
    request_secret = request.session['request_token_secret'].encode('utf-8')
    request_token = tokens.RequestToken(key=request_key, secret=request_secret)
    access_token = handshaker.complete(request_token, 'oauth_verifier=' + oauth_verifier + '&oauth_token=' + oauth_token)
    response = HttpResponseRedirect('https://wpx.wmflabs.org/requests/' + request.session['langcode'])
    response.session['access_token'] = access_token
    return response