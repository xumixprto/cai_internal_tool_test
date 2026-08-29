from django.urls import path

from apps.demo_two import views

app_name = "demo_two"
urlpatterns = [
    path("", views.index, name="index"),
]
