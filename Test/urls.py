from django.contrib import admin
from django.urls import include, path
from common import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home_view, name='home'),
    path('clearance/', include("clearance_system.urls")),
    path('contact/', views.contact_us, name='contact_us'),
    path('help-desk/', views.help_desk, name='help_desk'),
    path('about-us/', views.about_us, name='about_us'),
    path('testimonials/', views.testimonials, name='testimonials'),
    path('faqs/', views.faqs, name='faqs'),
    path('clearance-guide/', views.clearance_guide, name='clearance_guide'),
    path("", include("common.urls")),   
]