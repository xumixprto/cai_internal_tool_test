"""Vendor provider abstraction and a local mock implementation."""

import uuid


class VendorProvider:
    """Provider interface for validating a vendor application."""

    def validate_vendor(self, vendor):
        """Validate ``vendor`` and return mock validation information."""
        raise NotImplementedError


class LocalVendorProvider(VendorProvider):
    """Mock provider that returns a fake vendor validation result."""

    def validate_vendor(self, vendor):
        return {
            "valid": True,
            "company_status": "active",
            "validation_reference": f"VND-{uuid.uuid4().hex[:12].upper()}",
            "country": vendor.country,
        }
