"""KYC review domain model."""

from django.db import models

from shared.models.base import TimestampedModel


class KYCApplication(TimestampedModel):
    """A synthetic KYC case pending review and risk assessment."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        UNDER_REVIEW = "under_review", "Under Review"
        ESCALATED = "escalated", "Escalated"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class DocumentType(models.TextChoices):
        PASSPORT = "passport", "Passport"
        NATIONAL_ID = "national_id", "National ID"
        DRIVERS_LICENSE = "drivers_license", "Driver's License"

    class ProviderVerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        FAILED = "failed", "Failed"
        FLAGGED = "flagged", "Flagged"

    customer_name = models.CharField(max_length=200)
    customer_identifier = models.CharField(max_length=100, unique=True)
    country = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        default=DocumentType.PASSPORT,
    )
    document_identifier = models.CharField(max_length=100)
    risk_score = models.PositiveSmallIntegerField(default=50)
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.MEDIUM,
    )
    provider_verification_status = models.CharField(
        max_length=20,
        choices=ProviderVerificationStatus.choices,
        default=ProviderVerificationStatus.PENDING,
    )
    screening_flags = models.CharField(
        max_length=200,
        blank=True,
        help_text="Short screening summary, e.g. 'Sanctions clear; PEP flag'.",
    )
    provider_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["risk_level", "-created_at"]),
            models.Index(fields=["provider_verification_status", "-created_at"]),
            models.Index(fields=["customer_name"]),
            models.Index(fields=["country"]),
            models.Index(fields=["customer_identifier"]),
        ]

    def __str__(self):
        return f"KYC #{self.pk} — {self.customer_name} ({self.status})"
