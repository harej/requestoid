from . import config
from django.shortcuts import render
from mwoauth import ConsumerToken, Handshaker, tokens


def requests_handshaker():
    consumer_key = config.OAUTH_CONSUMER_KEY
    consumer_secret = config.OAUTH_CONSUMER_SECRET
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
