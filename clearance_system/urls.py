from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "clearance"

urlpatterns = [
    path("", views.home, name="home"),
    # The app has its own login/logout, so it never touches the host site's login.
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="clearance_system/login.html",
            next_page=reverse_lazy("clearance:home"),
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page=reverse_lazy("clearance:login")),
        name="logout",
    ),
    path("student/", views.student_dashboard, name="student_dashboard"),
    path("student/faculty/", views.choose_faculty, name="choose_faculty"),
    path("student/submit/", views.submit_request, name="submit_request"),
    path("student/resubmit/<int:pk>/", views.resubmit, name="resubmit"),
    path("certificate/<int:pk>/", views.certificate, name="certificate"),
    path("office/", views.office_queue, name="office_queue"),
    path("office/decide/<int:pk>/", views.decide, name="decide"),
]
