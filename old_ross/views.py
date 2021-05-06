from django.shortcuts import render

# Create your views here.


def index(request):

    return render(request, 'old_ross/index.html', {
    })
