from django.urls import path

from apps.demo_one import views

app_name = "demo_one"
urlpatterns = [
    path("", views.index, name="index"),
]
