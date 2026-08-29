from core.app_registry.manifest import AppAction, AppManifest

manifest = AppManifest(
    key="vendors",
    name="Vendor Approval",
    description="Review and approve vendor applications.",
    icon="shop",
    url_name="vendors:index",
    access_permission="vendors.access",
    actions=[
        AppAction(key="approve", permission="vendors.approve", label="Approve"),
        AppAction(key="reject", permission="vendors.reject", label="Reject"),
        AppAction(key="assign", permission="vendors.assign", label="Assign"),
        AppAction(
            key="request_changes", permission="vendors.request_changes", label="Request Changes"
        ),
    ],
    order=200,
)
