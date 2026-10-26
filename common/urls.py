from django.contrib import admin
from django.urls import path
from common import views
from . import views

urlpatterns = [
    path('contact/', views.contact_us, name='contact_us'),
    path('help-desk/', views.help_desk, name='help_desk'),
    path('about-us/', views.about_us, name='about_us'),
    path('testimonials/', views.testimonials, name='testimonials'),
    path('faqs/', views.faqs, name='faqs'),
    path('clearance-guide/', views.clearance_guide, name='clearance_guide'),
    path("status/", views.system_status, name="system_status"),
    path("health/", views.health_check, name="health_check"),
]