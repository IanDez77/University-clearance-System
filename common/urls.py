from django.contrib import admin
from django.urls import path
from common import views

urlpatterns = [
    path('contact/', views.contact_us, name='contact_us'),
    path('help-desk/', views.help_desk, name='help_desk'),
    path('about-us/', views.about_us, name='about_us'),
]