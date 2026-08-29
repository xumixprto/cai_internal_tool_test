from django.urls import path

from core.authentication import views

app_name = "core_authentication"
urlpatterns = [
    path("login/", views.PlatformLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
]
