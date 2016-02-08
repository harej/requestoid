from django.shortcuts import render
from django.template import Context

def select_language(request):
    available = {
                     'en': 'English'
                }

    context = Context({
                  'language': 'en',
                  'languages_available': available
              })

    return render(request, 'requestoid/select_language.html', context = context)