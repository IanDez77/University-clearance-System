from django.contrib import admin
from django.urls import include, path
from common import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home_view, name='home'),
    path('clearance/', include("clearance_system.urls")),
]