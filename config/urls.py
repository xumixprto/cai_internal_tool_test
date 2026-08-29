"""Root URL configuration for the Internal Tools Platform."""

from django.contrib import admin
from django.urls import include, path

from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.authentication.urls")),
    path("platform-admin/", include("core.admin_panel.urls")),
    path("", core_views.dashboard, name="dashboard"),
    # Developer-only component showcase.  The view raises 404 when DEBUG is False.
    path("dev/components/", core_views.components_showcase, name="dev_components"),
]

# Business applications are mounted under /apps/<app-key>/ by convention.
# Example:
#   path("apps/refunds/", include("apps.refunds.urls")),

handler403 = "core.views.permission_denied"
