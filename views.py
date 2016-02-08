from django.shortcuts import get_object_or_404, render

def select_language(request):
    return render(request, 'requestoid/select_language.html', {})
