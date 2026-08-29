from core.app_registry.manifest import AppAction, AppManifest

manifest = AppManifest(
    key="kyc",
    name="KYC Review",
    description="Review Know-Your-Customer cases and verify identity risk.",
    icon="shield-lock",
    url_name="kyc:index",
    access_permission="kyc.access",
    actions=[
        AppAction(key="approve", permission="kyc.approve", label="Approve"),
        AppAction(key="reject", permission="kyc.reject", label="Reject"),
        AppAction(key="escalate", permission="kyc.escalate", label="Escalate"),
        AppAction(key="assign", permission="kyc.assign", label="Assign"),
    ],
    order=300,
)
