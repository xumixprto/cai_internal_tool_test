"""Refund app URL configuration."""

from django.urls import path

from apps.refunds import views

app_name = "refunds"

urlpatterns = [
    path("", views.RefundQueueView.as_view(), name="index"),
    path("<int:pk>/", views.RefundDetailView.as_view(), name="detail"),
    path("<int:pk>/approve/", views.RefundApproveView.as_view(), name="approve"),
    path("<int:pk>/reject/", views.RefundRejectView.as_view(), name="reject"),
    path("<int:pk>/assign/", views.RefundAssignView.as_view(), name="assign"),
    path("<int:pk>/note/", views.RefundNoteView.as_view(), name="note"),
]
