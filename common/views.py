from django.shortcuts import render, redirect
from .models import ContactMessage


def base_view(request):
    context = {}
    return render(request, 'common/base.html', context)

def home_view(request):
    context = {}
    return render(request, 'common/home.html', context)

def help_desk(request):
    return render(request, "common/help_desk.html")

def about_us(request):
    return render(request, "common/about_us.html")

def contact_us(request):
    if request.method == "POST":
        ContactMessage.objects.create(
            name=request.POST.get("name"),
            email=request.POST.get("email"),
            message=request.POST.get("message")
        )
        return redirect("contact_us")
    
    return render(request, "common/contact_us.html")