"""Test-only application URLs for route authorization tests."""

from django.urls import path

from core.tests import views

app_name = "test_apps"

urlpatterns = [
    path("test-one/", views.test_one_index, name="test_one_index"),
    path("test-two/", views.test_two_index, name="test_two_index"),
]
