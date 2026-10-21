from django.shortcuts import render


def base_view(request):
    context = {}
    return render(request, 'common/base.html', context)


def home_view(request):
    context = {}
    return render(request, 'common/home.html', context)
