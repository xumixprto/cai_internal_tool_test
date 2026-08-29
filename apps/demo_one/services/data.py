from apps.demo_one.providers.status_provider import DemoOneStatusProvider


class DemoOneDataService:
    """Business service for Demo App One."""

    @staticmethod
    def list_items():
        """Return placeholder operational data."""
        labels = ["Example A", "Example B", "Example C"]
        statuses = DemoOneStatusProvider.get_statuses()
        return [{"name": label, "status": status} for label, status in zip(labels, statuses)]
