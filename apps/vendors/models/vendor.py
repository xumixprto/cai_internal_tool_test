"""Vendor application domain model."""

from django.db import models

from shared.models.base import TimestampedModel


class VendorApplication(TimestampedModel):
    """A vendor application pending review and approval."""

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        CHANGES_REQUESTED = "changes_requested", "Changes Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Category(models.TextChoices):
        SERVICES = "services", "Services"
        SOFTWARE = "software", "Software"
        HARDWARE = "hardware", "Hardware"
        CONSULTING = "consulting", "Consulting"
        FACILITIES = "facilities", "Facilities"

    company_name = models.CharField(max_length=200)
    contact_email = models.EmailField()
    country = models.CharField(max_length=100)
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.SERVICES,
    )
    tax_id = models.CharField(max_length=100)
    estimated_annual_spend = models.DecimalField(max_digits=15, decimal_places=2)
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["risk_level", "-created_at"]),
            models.Index(fields=["category", "-created_at"]),
            models.Index(fields=["company_name"]),
            models.Index(fields=["country"]),
        ]

    def __str__(self):
        return f"Vendor #{self.pk} — {self.company_name} ({self.status})"
