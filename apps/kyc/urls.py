"""KYC app URL configuration."""

from django.urls import path

from apps.kyc import views

app_name = "kyc"

urlpatterns = [
    path("", views.KYCQueueView.as_view(), name="index"),
    path("<int:pk>/", views.KYCDetailView.as_view(), name="detail"),
    path("<int:pk>/review/", views.KYCReviewView.as_view(), name="review"),
    path("<int:pk>/approve/", views.KYCApproveView.as_view(), name="approve"),
    path("<int:pk>/reject/", views.KYCRejectView.as_view(), name="reject"),
    path("<int:pk>/escalate/", views.KYCEscalateView.as_view(), name="escalate"),
    path("<int:pk>/assign/", views.KYCAssignView.as_view(), name="assign"),
    path("<int:pk>/note/", views.KYCNoteView.as_view(), name="note"),
]
