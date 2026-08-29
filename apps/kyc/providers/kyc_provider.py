"""KYC provider abstraction and a local mock implementation."""

import uuid


class KYCProvider:
    """Provider interface for verifying an identity for a KYC case."""

    def verify_identity(self, case):
        """Verify ``case`` and return mock KYC/screening information."""
        raise NotImplementedError


class LocalKYCProvider(KYCProvider):
    """Mock provider that returns deterministic KYC verification results.

    Results are derived from the document identifier so tests and demo data can
    control outcomes without needing a real identity service.
    """

    def verify_identity(self, case):
        doc_id = case.document_identifier.upper()
        if doc_id.endswith("FAIL"):
            return {
                "identity_match": True,
                "document_verified": False,
                "screening_result": "failed",
                "screening_flags": "Document could not be verified",
                "provider_reference": f"KYC-{uuid.uuid4().hex[:12].upper()}",
            }
        if doc_id.endswith("FLAG"):
            return {
                "identity_match": True,
                "document_verified": True,
                "screening_result": "flagged",
                "screening_flags": "PEP match; sanctions clear",
                "provider_reference": f"KYC-{uuid.uuid4().hex[:12].upper()}",
            }
        return {
            "identity_match": True,
            "document_verified": True,
            "screening_result": "clear",
            "screening_flags": "Sanctions clear; PEP clear",
            "provider_reference": f"KYC-{uuid.uuid4().hex[:12].upper()}",
        }
