from core.app_registry.manifest import AppAction, AppManifest

manifest = AppManifest(
    key="refunds",
    name="Refund Review",
    description="Review and process customer refund requests.",
    icon="credit-card",
    url_name="refunds:index",
    access_permission="refunds.access",
    actions=[
        AppAction(key="approve", permission="refunds.approve", label="Approve"),
        AppAction(key="reject", permission="refunds.reject", label="Reject"),
        AppAction(key="assign", permission="refunds.assign", label="Assign"),
    ],
    order=100,
)
