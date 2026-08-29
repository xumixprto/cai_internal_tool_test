from django.urls import path

from core.admin_panel import views

app_name = "core_admin_panel"
urlpatterns = [
    path("", views.user_list, name="index"),
    path("users/<int:user_id>/", views.user_edit, name="user_edit"),
]
