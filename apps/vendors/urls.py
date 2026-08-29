"""Vendor app URL configuration."""

from django.urls import path

from apps.vendors import views

app_name = "vendors"

urlpatterns = [
    path("", views.VendorQueueView.as_view(), name="index"),
    path("<int:pk>/", views.VendorDetailView.as_view(), name="detail"),
    path("<int:pk>/review/", views.VendorReviewView.as_view(), name="review"),
    path("<int:pk>/approve/", views.VendorApproveView.as_view(), name="approve"),
    path("<int:pk>/reject/", views.VendorRejectView.as_view(), name="reject"),
    path(
        "<int:pk>/request-changes/",
        views.VendorRequestChangesView.as_view(),
        name="request_changes",
    ),
    path("<int:pk>/assign/", views.VendorAssignView.as_view(), name="assign"),
    path("<int:pk>/note/", views.VendorNoteView.as_view(), name="note"),
]
