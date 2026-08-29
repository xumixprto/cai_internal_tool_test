"""Seed example refund requests for local demos."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.refunds.models.refund import RefundRequest

User = get_user_model()


class Command(BaseCommand):
    """Create a realistic set of refund requests for demonstration."""

    help = "Seed refund demo data (idempotent: avoids duplicates by transaction ID)."

    def handle(self, *args, **options):
        demo_data = [
            (
                "TXN-1001",
                "Alice Smith",
                "alice@example.com",
                Decimal("120.00"),
                "USD",
                "Duplicate charge",
            ),
            (
                "TXN-1002",
                "Bob Jones",
                "bob@example.com",
                Decimal("45.50"),
                "USD",
                "Customer canceled order",
            ),
            (
                "TXN-1003",
                "Carol White",
                "carol@example.com",
                Decimal("230.00"),
                "USD",
                "Product not received",
            ),
            (
                "TXN-1004",
                "Dan Brown",
                "dan@example.com",
                Decimal("15.99"),
                "USD",
                "Overcharged shipping",
            ),
            (
                "TXN-1005",
                "Eve Miller",
                "eve@example.com",
                Decimal("89.00"),
                "EUR",
                "Wrong item delivered",
            ),
            (
                "TXN-1006",
                "Frank Wilson",
                "frank@example.com",
                Decimal("310.00"),
                "EUR",
                "Service outage credit",
            ),
            (
                "TXN-1007",
                "Grace Lee",
                "grace@example.com",
                Decimal("55.00"),
                "GBP",
                "Return within window",
            ),
            (
                "TXN-1008",
                "Henry Taylor",
                "henry@example.com",
                Decimal("199.00"),
                "USD",
                "Defective product",
            ),
            (
                "TXN-1009",
                "Ivy Davis",
                "ivy@example.com",
                Decimal("12.30"),
                "GBP",
                "Subscription cancelled",
            ),
            (
                "TXN-1010",
                "Jack Garcia",
                "jack@example.com",
                Decimal("430.00"),
                "EUR",
                "Fraudulent transaction",
            ),
            (
                "TXN-1011",
                "Karen Martinez",
                "karen@example.com",
                Decimal("75.00"),
                "USD",
                "Late delivery",
            ),
            (
                "TXN-1012",
                "Leo Anderson",
                "leo@example.com",
                Decimal("150.00"),
                "USD",
                "Wrong size",
            ),
            (
                "TXN-1013",
                "Mia Thomas",
                "mia@example.com",
                Decimal("22.00"),
                "USD",
                "Duplicate subscription",
            ),
            (
                "TXN-1014",
                "Noah Jackson",
                "noah@example.com",
                Decimal("540.00"),
                "EUR",
                "Refund per support",
            ),
            (
                "TXN-1015",
                "Olivia Harris",
                "olivia@example.com",
                Decimal("8.99"),
                "GBP",
                "Tax overcharge",
            ),
            (
                "TXN-1016",
                "Paul Clark",
                "paul@example.com",
                Decimal("95.00"),
                "USD",
                "Unrecognized charge",
            ),
            (
                "TXN-1017",
                "Quinn Lewis",
                "quinn@example.com",
                Decimal("180.00"),
                "USD",
                "Item returned",
            ),
            (
                "TXN-1018",
                "Ray Robinson",
                "ray@example.com",
                Decimal("60.00"),
                "EUR",
                "Account credit",
            ),
            (
                "TXN-1019",
                "Sophia Walker",
                "sophia@example.com",
                Decimal("275.00"),
                "USD",
                "Double payment",
            ),
            (
                "TXN-1020",
                "Tom Hall",
                "tom@example.com",
                Decimal("42.00"),
                "GBP",
                "Promo not applied",
            ),
            (
                "TXN-1021",
                "Uma Young",
                "uma@example.com",
                Decimal("130.00"),
                "USD",
                "Canceled flight leg",
            ),
            (
                "TXN-1022",
                "Victor King",
                "victor@example.com",
                Decimal("19.99"),
                "USD",
                "App store duplicate",
            ),
            (
                "TXN-1023",
                "Wendy Wright",
                "wendy@example.com",
                Decimal("360.00"),
                "EUR",
                "Refund for outage",
            ),
            (
                "TXN-1024",
                "Xavier Lopez",
                "xavier@example.com",
                Decimal("88.00"),
                "GBP",
                "Overdraft fee refund",
            ),
            (
                "TXN-1025",
                "Yara Hill",
                "yara@example.com",
                Decimal("210.00"),
                "USD",
                "Billing error",
            ),
            (
                "TXN-1026",
                "Zack Green",
                "zack@example.com",
                Decimal("33.50"),
                "USD",
                "Membership refund",
            ),
        ]

        statuses = [
            RefundRequest.Status.PENDING,
            RefundRequest.Status.UNDER_REVIEW,
            RefundRequest.Status.APPROVED,
            RefundRequest.Status.APPROVED,
            RefundRequest.Status.REJECTED,
            RefundRequest.Status.PENDING,
            RefundRequest.Status.UNDER_REVIEW,
        ]

        created = 0
        for index, (
            transaction_id,
            customer_name,
            customer_email,
            amount,
            currency,
            reason,
        ) in enumerate(demo_data):
            refund, new = RefundRequest.objects.get_or_create(
                transaction_id=transaction_id,
                defaults={
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "amount": amount,
                    "currency": currency,
                    "reason": reason,
                    "status": statuses[index % len(statuses)],
                },
            )
            if new:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} refund request(s)."))
