"""Root URL configuration for the Internal Tools Platform."""

from django.contrib import admin
from django.urls import include, path

from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.authentication.urls")),
    path("platform-admin/", include("core.admin_panel.urls")),
    path("", core_views.dashboard, name="dashboard"),
]

handler403 = "core.views.permission_denied"
