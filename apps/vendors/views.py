"""Vendor app views."""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.html import format_html
from django.views import View
from django.views.generic import DetailView, ListView

from apps.vendors.forms import (
    VendorAssignForm,
    VendorFilterForm,
    VendorNoteForm,
    VendorRejectForm,
    VendorRequestChangesForm,
)
from apps.vendors.models.vendor import VendorApplication
from apps.vendors.services.vendors import VendorService, VendorServiceError
from core.navigation.breadcrumbs import app_breadcrumbs
from core.rbac.mixins import AppAccessRequiredMixin, AppActionRequiredMixin
from core.rbac.services import can_perform_action
from shared.services.primitives import assignments


class VendorQueueView(AppAccessRequiredMixin, ListView):
    """Operational vendor approval queue with filters and pagination."""

    app_key = "vendors"
    model = VendorApplication
    template_name = "vendors/queue.html"
    context_object_name = "vendors"
    paginate_by = 10

    def get_queryset(self):
        qs = VendorApplication.objects.order_by("-created_at")
        self.filter_form = VendorFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            data = self.filter_form.cleaned_data
            if data.get("status"):
                qs = qs.filter(status=data["status"])
            if data.get("risk"):
                qs = qs.filter(risk_level=data["risk"])
            search = (data.get("q") or "").strip()
            if search:
                qs = qs.filter(
                    Q(company_name__icontains=search)
                    | Q(tax_id__icontains=search)
                    | Q(country__icontains=search)
                )
            assigned_to = data.get("assigned_to")
            if assigned_to:
                qs = self._filter_by_current_assignee(qs, assigned_to)
        return qs

    def _filter_by_current_assignee(self, qs, assigned_to):
        return qs.filter(pk__in=assignments.currently_assigned_to(VendorApplication, assigned_to))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = getattr(self, "filter_form", VendorFilterForm(self.request.GET))
        get_copy = self.request.GET.copy()
        get_copy.pop("page", None)
        context["extra_params"] = "&" + get_copy.urlencode() if get_copy else ""
        context["page_title"] = "Vendor Approval"
        vendors = list(context["vendors"])
        context["current_assignments"] = _current_assignment_map([v.pk for v in vendors])
        context["table_headers"] = [
            "Company",
            "Country",
            "Category",
            "Risk",
            "Est. Spend",
            "Status",
            "Assigned To",
            "Submitted",
        ]
        context["table_rows"] = [
            self._build_table_row(vendor, context["current_assignments"]) for vendor in vendors
        ]
        context["safe"] = True
        context["action_column"] = True
        return context

    def _build_table_row(self, vendor, current_assignments):
        assignments_map = current_assignments
        assignee = assignments_map.get(vendor.pk)
        detail_url = reverse("vendors:detail", args=[vendor.pk])
        action = format_html(
            '<a class="btn btn-sm btn-outline-primary" href="{0}">View</a>',
            detail_url,
        )
        status_badge = format_html(
            '<span class="badge rounded-pill bg-{0}">{1}</span>',
            _badge_style(vendor.status),
            vendor.get_status_display(),
        )
        risk_badge = format_html(
            '<span class="badge rounded-pill bg-{0}">{1}</span>',
            _risk_badge_style(vendor.risk_level),
            vendor.get_risk_level_display(),
        )
        return [
            format_html(
                "<strong>{0}</strong><br><small class='text-muted'>{1}</small>",
                vendor.company_name,
                vendor.contact_email,
            ),
            vendor.country,
            vendor.get_category_display(),
            risk_badge,
            format_html("{0} USD", vendor.estimated_annual_spend),
            status_badge,
            assignee.assigned_to.username if assignee else "—",
            vendor.created_at.strftime("%Y-%m-%d %H:%M"),
            action,
        ]


class VendorDetailView(AppAccessRequiredMixin, DetailView):
    """Vendor detail with actions, notes, and activity history."""

    app_key = "vendors"
    model = VendorApplication
    template_name = "vendors/detail.html"
    context_object_name = "vendor"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendor = context["vendor"]
        user = self.request.user
        context["page_title"] = f"Vendor #{vendor.pk}"
        context["breadcrumbs"] = app_breadcrumbs(
            app_key="vendors",
            object_label=f"Vendor #{vendor.pk}",
        )
        context["current_assignment"] = VendorService().get_current_assignment(vendor)
        context["activity"] = VendorService().get_activity(vendor)
        context["notes"] = VendorService().get_notes(vendor)
        can_approve = can_perform_action(user, "vendors", "approve")
        context["can_approve"] = can_approve
        context["can_reject"] = can_perform_action(user, "vendors", "reject")
        context["can_assign"] = can_perform_action(user, "vendors", "assign")
        context["can_request_changes"] = can_perform_action(user, "vendors", "request_changes")
        context["can_start_review"] = can_approve and vendor.status in (
            VendorApplication.Status.SUBMITTED,
            VendorApplication.Status.CHANGES_REQUESTED,
        )
        context["can_approve_action"] = (
            can_approve and vendor.status == VendorApplication.Status.UNDER_REVIEW
        )
        context["is_terminal"] = vendor.status in (
            VendorApplication.Status.APPROVED,
            VendorApplication.Status.REJECTED,
        )
        context["status_badge_style"] = _badge_style(vendor.status)
        context["risk_badge_style"] = _risk_badge_style(vendor.risk_level)
        context["reject_form"] = VendorRejectForm()
        context["request_changes_form"] = VendorRequestChangesForm()
        context["assign_form"] = VendorAssignForm()
        context["note_form"] = VendorNoteForm()
        return context


class VendorReviewView(AppActionRequiredMixin, View):
    """Move a vendor application to under review."""

    app_key = "vendors"
    action_key = "approve"

    def post(self, request, pk):
        vendor = get_object_or_404(VendorApplication, pk=pk)
        try:
            VendorService().move_to_under_review(vendor, request.user)
            messages.success(request, "Vendor application is now under review.")
        except VendorServiceError as exc:
            messages.error(request, str(exc))
        return redirect(reverse("vendors:detail", args=[pk]))


class VendorApproveView(AppActionRequiredMixin, View):
    """Approve a vendor application."""

    app_key = "vendors"
    action_key = "approve"

    def post(self, request, pk):
        vendor = get_object_or_404(VendorApplication, pk=pk)
        try:
            VendorService().approve(vendor, request.user)
            messages.success(request, "Vendor application approved.")
        except VendorServiceError as exc:
            messages.error(request, str(exc))
        return redirect(reverse("vendors:detail", args=[pk]))


class VendorRejectView(AppActionRequiredMixin, View):
    """Reject a vendor application with a reason."""

    app_key = "vendors"
    action_key = "reject"

    def post(self, request, pk):
        vendor = get_object_or_404(VendorApplication, pk=pk)
        form = VendorRejectForm(request.POST)
        if form.is_valid():
            try:
                VendorService().reject(vendor, request.user, form.cleaned_data["reason"])
                messages.success(request, "Vendor application rejected.")
            except VendorServiceError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Please provide a rejection reason.")
        return redirect(reverse("vendors:detail", args=[pk]))


class VendorRequestChangesView(AppActionRequiredMixin, View):
    """Request changes on a vendor application."""

    app_key = "vendors"
    action_key = "request_changes"

    def post(self, request, pk):
        vendor = get_object_or_404(VendorApplication, pk=pk)
        form = VendorRequestChangesForm(request.POST)
        if form.is_valid():
            try:
                VendorService().request_changes(vendor, request.user, form.cleaned_data["reason"])
                messages.success(request, "Changes requested.")
            except VendorServiceError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Please provide the requested changes.")
        return redirect(reverse("vendors:detail", args=[pk]))


class VendorAssignView(AppActionRequiredMixin, View):
    """Assign a vendor application to a user."""

    app_key = "vendors"
    action_key = "assign"

    def post(self, request, pk):
        vendor = get_object_or_404(VendorApplication, pk=pk)
        form = VendorAssignForm(request.POST)
        if form.is_valid():
            try:
                VendorService().assign(
                    vendor,
                    form.cleaned_data["assigned_to"],
                    request.user,
                )
                messages.success(request, "Vendor application assigned.")
            except VendorServiceError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Please select a user to assign.")
        return redirect(reverse("vendors:detail", args=[pk]))


class VendorNoteView(AppAccessRequiredMixin, View):
    """Add a note to a vendor application."""

    app_key = "vendors"

    def post(self, request, pk):
        vendor = get_object_or_404(VendorApplication, pk=pk)
        form = VendorNoteForm(request.POST)
        if form.is_valid():
            try:
                VendorService().add_note(vendor, request.user, form.cleaned_data["body"])
                messages.success(request, "Note added.")
            except VendorServiceError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Please enter a note.")
        return redirect(reverse("vendors:detail", args=[pk]))


def _badge_style(status: str) -> str:
    return {
        VendorApplication.Status.SUBMITTED: "secondary",
        VendorApplication.Status.UNDER_REVIEW: "info",
        VendorApplication.Status.CHANGES_REQUESTED: "warning",
        VendorApplication.Status.APPROVED: "success",
        VendorApplication.Status.REJECTED: "danger",
    }.get(status, "secondary")


def _risk_badge_style(risk: str) -> str:
    return {
        VendorApplication.RiskLevel.LOW: "success",
        VendorApplication.RiskLevel.MEDIUM: "info",
        VendorApplication.RiskLevel.HIGH: "warning",
        VendorApplication.RiskLevel.CRITICAL: "danger",
    }.get(risk, "secondary")


def _current_assignment_map(vendor_ids):
    return assignments.latest_map_for(VendorApplication, object_ids=vendor_ids)
