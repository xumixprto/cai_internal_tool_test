"""Root URL configuration for tests requiring test application URLs."""

from django.urls import include, path

urlpatterns = [
    path("", include("config.urls")),
    path("test/", include("core.tests.test_app_urls")),
]

handler403 = "core.views.permission_denied"
