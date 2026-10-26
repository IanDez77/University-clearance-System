from django.shortcuts import render, redirect
from .models import ContactMessage
from django.http import JsonResponse
from django.db import connection
from django.shortcuts import render


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

def testimonials(request):
    return render(request, "common/testimonials.html")

def faqs(request):
    return render(request, "common/faqs.html")   

def clearance_guide(request):
    return render(request, "common/clearance_guide.html") 

def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return JsonResponse({
            "status": "operational",
            "application": "online",
            "database": "online",
        })

    except Exception:
        return JsonResponse({
            "status": "degraded",
            "application": "online",
            "database": "offline",
        }, status=503)


def system_status(request):
    return render(request, "common/status.html")