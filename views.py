from django.shortcuts import render

def select_language(request):
    available = {
                     'en': 'English'
                }

    context = {
                  'language': 'en',
                  'available': available
              }

    return render(request, 'requestoid/select_language.html', context = context)