import configparser
import os
from django.shortcuts import render
from mwoauth import ConsumerToken, Handshaker, tokens

def requests_handshaker(ROOTDIR):
    keyfile = configparser.ConfigParser()
    keyfile.read([os.path.expanduser(ROOTDIR + '/.oauth.ini')])
    consumer_key = keyfile.get('oauth', 'consumer_key')
    consumer_secret = keyfile.get('oauth', 'consumer_secret')
    consumer_token = ConsumerToken(consumer_key, consumer_secret)
    return Handshaker("https://meta.wikimedia.org/w/index.php", consumer_token)

def get_username(request, ROOTDIR):
    handshaker = requests_handshaker(ROOTDIR)
    if 'access_token_key' in request.session:
        access_key = request.session['access_token_key'].encode('utf-8')
        access_secret = request.session['access_token_secret'].encode('utf-8')
        access_token = tokens.AccessToken(key=access_key, secret=access_secret)
        return handshaker.identify(access_token)['username']
    else:
        return None

def you_need_to_login(request, langcode):
    content = {
                  'headline': _('Login required'),
                  'explanation': _('login_required_message')
              }

    context = {
                  'interface': interface_messages(request, langcode),
                  'language': langcode,
                  'content': content
              }

    return render(request, 'requestoid/error.html', context = context)
