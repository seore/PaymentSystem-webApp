from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from payapp.views import logout_view

urlpatterns = [
    path("admin/", admin.site.urls),

    path("login/", auth_views.LoginView.as_view(
        template_name="registration/login.html"
    ), name="login"),

    # our custom logout
    path("logout/", logout_view, name="logout"),

    path("", include("payapp.urls")),
]
