from django.shortcuts import render

def select_language(request):
	languages_available = {
	                          'en': 'English'
	                      }

	context = {
	              'language': 'en',
	              'languages_available': languages_available
	          }

    return render(request, 'requestoid/select_language.html', context = context)