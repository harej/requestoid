import configparser
import os
from . import wiki
from django.shortcuts import render
from django.http.response import HttpResponseRedirect
from mwoauth import ConsumerToken, Handshaker, tokens
from worldly import Worldly

# Views! Views! Views, views, views, views, views views views views views views has a has a has a has a kind of mystery

ROOTDIR = '/var/www/django-src/requestoid/requestoid'
LOCALEDIR = ROOTDIR + '/locale'
translation = Worldly(ROOTDIR + "/i18n.yaml")
_ = translation.render


def requests_handshaker():
    keyfile = configparser.ConfigParser()
    keyfile.read([os.path.expanduser(ROOTDIR + '/.oauth.ini')])
    consumer_key = keyfile.get('oauth', 'consumer_key')
    consumer_secret = keyfile.get('oauth', 'consumer_secret')
    consumer_token = ConsumerToken(consumer_key, consumer_secret)
    return Handshaker("https://meta.wikimedia.org/w/index.php", consumer_token)


def get_username(request):
    handshaker = requests_handshaker()
    if 'access_token_key' in request.session:
        access_key = request.session['access_token_key'].encode('utf-8')
        access_secret = request.session['access_token_secret'].encode('utf-8')
        access_token = tokens.AccessToken(key=access_key, secret=access_secret)
        return handshaker.identify(access_token)['username']
    else:
        return None


def interface_messages(request, langcode):
    '''
    Provides a dictionary to feed into the context, with an ISO 639-1 or -2 language code as input.
    '''

    translation.use_language = langcode

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
    translation.use_language = langcode

    content = {
                  'headline': _('Help fill in the gaps on Wikipedia'),
                  'intro': _('homepage_intro')
              }

    context = {
                  'interface': interface_messages(request, langcode),
                  'language': langcode,
                  'content': content
              }

    return render(request, 'requestoid/homepage.html', context = context)


def auth(request):  # /requests/auth
    handshaker = requests_handshaker()
    redirect, request_token = handshaker.initiate()
    request.session['request_token_key'] = request_token.key.decode('utf-8')
    request.session['request_token_secret'] = request_token.secret.decode('utf-8')
    request.session['return_to'] = request.META['HTTP_REFERER']
    return HttpResponseRedirect(redirect)  # This hands the user off to Wikimedia; user returns to the website via the callback view which implements the session


def callback(request):  # /requests/callback
    oauth_verifier = request.GET['oauth_verifier']
    oauth_token = request.GET['oauth_token']
    handshaker = requests_handshaker()
    request_key = request.session['request_token_key'].encode('utf-8')
    request_secret = request.session['request_token_secret'].encode('utf-8')
    request_token = tokens.RequestToken(key=request_key, secret=request_secret)
    access_token = handshaker.complete(request_token, 'oauth_verifier=' + oauth_verifier + '&oauth_token=' + oauth_token)
    request.session['access_token_key'] = access_token.key.decode('utf-8')
    request.session['access_token_secret'] = access_token.secret.decode('utf-8')
    return HttpResponseRedirect(request.session['return_to'])

def add(request, langcode):  # /requests/en/add
    translation.use_language = langcode

    if 'pagetitle' in request.GET:
        if request.GET['pagetitle'] != "":
            if request.GET['language'] == "":
                request_language = langcode
            else:
                request_language = request.GET['language']

            pagetitle = request.GET['pagetitle']
            pageid = wiki.GetPageId(request_language, pagetitle)
            content = {}
            content['category_label'] = _('Categories')
            content['wikiprojects_label'] = _('WikiProjects')
            content['summary_label'] = _('Summary')
            content['summary_explanation'] = _('Please provide a brief summary of your request.')

            # Does the article exist? Two different workflows if so.
            if pageid == None:  # new article workflow
                pageid = 0
                content['summary_inputbox'] = _('Create new article')
                content['category_explanation'] = _('Enter one category per line. Case sensitive. Do not include "Category:".')
                content['category_textarea'] = ''
                content['wikiprojects_explanation'] = _('Enter one WikiProject per line. Case sensitive. Include "WikiProject" if it is in the name.')
                content['wikiprojects_textarea'] = ''

            else:  # existing article workflow
                content['summary_inputbox'] = ''
                content['category_explanation'] = _('Categories are retrieved automatically from Wikipedia.')
                content['category_textarea'] = wiki.GetCategories(request_language, pageid)
                content['wikiprojects_explanation'] = _('WikiProjects are retrieved automatically from Wikipedia. You may add additional projects if you wish.')
                content['wikiprojects_textarea'] = wiki.GetWikiProjects(request_language, pagetitle)

            content['note_label'] = _('Add a note')
            content['note_explanation'] = _('Please expand on your request. It is recommended you include additional context and sources if you have any. You may use wikitext markup.')
            content['submit_button'] = _('add_submit_button')

            context = {
                        'interface': interface_messages(request, langcode),
                        'language': langcode,
                        'content': content,
                        'request_language': request_language,
                        'pagetitle': pagetitle,
                        'pageid': pageid
                      }

            return render(request, 'requestoid/add_details.html', context = context)

    # Default behavior for no pagetitle specified
    content = {
                'headline': _('add_start_headline'),
                'inputlabel': _('add_start_input_label'),
                'explanation': _('add_start_explanation'),
                'button': _('add_start_button_label')
              }

    context = {
                'interface': interface_messages(request, langcode),
                'language': langcode,
                'content': content
              }

    return render(request, 'requestoid/add_start.html', context = context)