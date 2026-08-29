from apps.demo_two.providers.status_provider import DemoTwoStatusProvider
from apps.demo_two.providers.type_provider import DemoTwoTypeProvider


class DemoTwoDataService:
    """Business service for Demo App Two."""

    @staticmethod
    def list_items():
        """Return placeholder operational data."""
        names = ["Example One", "Example Two", "Example Three"]
        types = DemoTwoTypeProvider.get_types()
        statuses = DemoTwoStatusProvider.get_statuses()
        return [
            {"name": name, "type": type_, "status": status}
            for name, type_, status in zip(names, types, statuses)
        ]
