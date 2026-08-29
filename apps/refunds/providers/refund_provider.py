"""Refund provider abstraction and a local mock implementation."""

import uuid


class RefundProvider:
    """Provider interface for processing refund payments."""

    def process_refund(self, refund):
        """Process ``refund`` and return an external provider reference."""
        raise NotImplementedError


class LocalRefundProvider(RefundProvider):
    """Mock provider that returns a fake external reference."""

    def process_refund(self, refund):
        return f"REF-{uuid.uuid4().hex[:12].upper()}"
