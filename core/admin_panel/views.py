from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.admin_panel.forms import UserAccessForm
from core.app_registry.services import set_user_app_access, sync_app_permissions
from core.rbac.decorators import admin_required
from core.rbac.roles import Role
from core.rbac.services import get_user_role, set_user_access

User = get_user_model()
PROTECTED_ADMIN_USERNAME = "admin"


@login_required(login_url="/login/")
@admin_required
def user_list(request):
    """Show the user management table."""
    users = User.objects.order_by("username")
    return render(
        request,
        "core_admin_panel/users.html",
        {
            "page_title": "Admin",
            "page_description": "User access management",
            "users": users,
            "protected_admin": PROTECTED_ADMIN_USERNAME,
        },
    )


@login_required(login_url="/login/")
@admin_required
def user_edit(request, user_id):
    """Edit role, active status, and application access for user1/user2 only."""
    target_user = get_object_or_404(User, pk=user_id)

    if target_user.username == PROTECTED_ADMIN_USERNAME:
        return render(
            request,
            "errors/403.html",
            {"page_title": "Access Denied"},
            status=403,
        )

    if request.method == "POST":
        form = UserAccessForm(request.POST, target_user=target_user)
        if form.is_valid():
            role = Role(form.cleaned_data["role"])
            set_user_access(target_user, role, form.cleaned_data["is_active"])
            # Ensure all app permissions exist before assigning them.
            sync_app_permissions()
            set_user_app_access(target_user, form.get_selected_app_keys())
            return redirect(reverse("core_admin_panel:index"))
    else:
        current_role = get_user_role(target_user)
        form = UserAccessForm(
            target_user=target_user,
            initial={
                "role": current_role.value if current_role else Role.USER.value,
                "is_active": target_user.is_active,
            },
        )

    return render(
        request,
        "core_admin_panel/edit_user.html",
        {
            "page_title": "Edit Access",
            "page_description": f"Edit access for {target_user.username}",
            "target_user": target_user,
            "form": form,
        },
    )
