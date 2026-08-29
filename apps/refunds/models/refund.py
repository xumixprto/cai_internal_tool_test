from django.db import models

from shared.models.base import TimestampedModel


class RefundRequest(TimestampedModel):
    """A customer refund request under review."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class Currency(models.TextChoices):
        USD = "USD", "USD"
        EUR = "EUR", "EUR"
        GBP = "GBP", "GBP"

    transaction_id = models.CharField(max_length=100)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD,
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    external_reference = models.CharField(max_length=200, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["customer_name", "-created_at"]),
            models.Index(fields=["transaction_id"]),
        ]

    def __str__(self):
        return f"Refund #{self.pk} — {self.customer_name} ({self.status})"
