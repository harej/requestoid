"""requestoid URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
import re
from django.conf.urls import url
from django.contrib import admin
from . import config, views

# Workaround for dev purposes
def pat(r):
    if config.DEBUG_STATUS is True:
        return r'^requests/' + r
    return r'^' + r

urlpatterns = [
    url(pat('admin/'), admin.site.urls),
    url(pat('$'), views.select_language),  # /requests
    url(pat('auth$'), views.auth),  # /requests/auth
    url(pat('callback$'), views.callback),  # /requests/callback
    url(pat('(?P<langcode>([^\/])*)$'), views.homepage),  # /requests/en
    url(pat('(?P<langcode>([^\/])*)\/add$'), views.add),  # /requests/en/add
    url(pat('(?P<langcode>([^\/])*)\/request\/(?P<reqid>(\d)+)$'), views.request),  # /requests/en/request/12345
    url(pat('(?P<langcode>([^\/])*)\/log$'), views.log),  # /requests/en/log
    url(pat('(?P<langcode>([^\/])*)\/search$'), views.search),  # /requests/en/search
    url(pat('(?P<langcode>([^\/])*)\/request$'), views.search),  # alias for above
    url(pat('(?P<langcode>([^\/])*)\/help$'), views.help),  # /requests/en/help
    url(pat('(?P<langcode>([^\/])*)\/about$'), views.about),  # /requests/en/about
]
