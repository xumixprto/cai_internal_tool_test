class DemoTwoTypeProvider:
    """Provider abstraction for item types."""

    @staticmethod
    def get_types():
        return ["Review", "Approval", "Review"]
