"""Root URL configuration for the Internal Tools Platform."""

from django.contrib import admin
from django.urls import include, path

from core.views import dashboard

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard, name="dashboard"),
    path("apps/demo-one/", include("apps.demo_one.urls")),
    path("apps/demo-two/", include("apps.demo_two.urls")),
]
