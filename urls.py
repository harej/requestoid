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
from django.conf.urls import url
from django.contrib import admin
from . import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', views.select_language),  # /requests
    url(r'^auth$', views.auth),  # /requests/auth
    url(r'^callback$', views.callback),  # /requests/callback
    url(r'^(?P<langcode>([^\/])*)$', views.homepage),  # /requests/en
    url(r'^(?P<langcode>([^\/])*)\/add$', views.add),  # /requests/en/add
    url(r'^(?P<langcode>([^\/])*)\/request\/(?P<reqid>(\d)+)$', views.request),  # /requests/en/request/12345
    url(r'^(?P<langcode>([^\/])*)\/log$', views.log),  # /requests/en/log
    url(r'^(?P<langcode>([^\/])*)\/search$', views.search),  # /requests/en/search
    url(r'^(?P<langcode>([^\/])*)\/request$', views.search),  # alias for above
    url(r'^(?P<langcode>([^\/])*)\/help$', views.help),  # /requests/en/help
    url(r'^(?P<langcode>([^\/])*)\/about$', views.about),  # /requests/en/about
]