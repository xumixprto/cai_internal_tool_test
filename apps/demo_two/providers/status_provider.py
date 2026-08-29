class DemoTwoStatusProvider:
    """Provider abstraction for item statuses."""

    @staticmethod
    def get_statuses():
        return ["Open", "Complete", "Open"]
