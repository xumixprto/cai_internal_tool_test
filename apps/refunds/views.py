"""Refund app views."""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.html import format_html
from django.views import View
from django.views.generic import DetailView, ListView

from apps.refunds.forms import (
    RefundAssignForm,
    RefundFilterForm,
    RefundNoteForm,
    RefundRejectForm,
)
from apps.refunds.models.refund import RefundRequest
from apps.refunds.services.refunds import RefundService, RefundServiceError
from core.navigation.breadcrumbs import app_breadcrumbs
from core.rbac.mixins import AppAccessRequiredMixin, AppActionRequiredMixin
from core.rbac.services import can_perform_action
from shared.services.primitives import assignments


class RefundQueueView(AppAccessRequiredMixin, ListView):
    """Operational refund review queue with filters and pagination."""

    app_key = "refunds"
    model = RefundRequest
    template_name = "refunds/queue.html"
    context_object_name = "refunds"
    paginate_by = 10

    def get_queryset(self):
        qs = RefundRequest.objects.order_by("-created_at")
        self.filter_form = RefundFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            data = self.filter_form.cleaned_data
            if data.get("status"):
                qs = qs.filter(status=data["status"])
            search = (data.get("q") or "").strip()
            if search:
                qs = qs.filter(
                    Q(customer_name__icontains=search)
                    | Q(transaction_id__icontains=search)
                    | Q(reason__icontains=search)
                )
            assigned_to = data.get("assigned_to")
            if assigned_to:
                qs = self._filter_by_current_assignee(qs, assigned_to)
        return qs

    def _filter_by_current_assignee(self, qs, assigned_to):
        return qs.filter(pk__in=assignments.currently_assigned_to(RefundRequest, assigned_to))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = getattr(self, "filter_form", RefundFilterForm(self.request.GET))
        get_copy = self.request.GET.copy()
        get_copy.pop("page", None)
        context["extra_params"] = "&" + get_copy.urlencode() if get_copy else ""
        context["page_title"] = "Refund Review"
        context["badge_style"] = _badge_style
        refunds = list(context["refunds"])
        context["current_assignments"] = _current_assignment_map([r.pk for r in refunds])
        context["table_headers"] = [
            "Customer",
            "Transaction",
            "Amount",
            "Reason",
            "Status",
            "Assigned To",
            "Requested",
        ]
        context["table_rows"] = [
            self._build_table_row(refund, context["current_assignments"]) for refund in refunds
        ]
        context["safe"] = True
        context["action_column"] = True
        return context

    def _build_table_row(self, refund, current_assignments):
        assignments_map = current_assignments
        assignee = assignments_map.get(refund.pk)
        detail_url = reverse("refunds:detail", args=[refund.pk])
        action = format_html(
            '<a class="btn btn-sm btn-outline-primary" href="{0}">View</a>',
            detail_url,
        )
        status_badge = format_html(
            '<span class="badge rounded-pill bg-{0}">{1}</span>',
            _badge_style(refund.status),
            refund.get_status_display(),
        )
        return [
            format_html(
                "<strong>{0}</strong><br><small class='text-muted'>{1}</small>",
                refund.customer_name,
                refund.customer_email,
            ),
            refund.transaction_id,
            format_html("{0} {1}", refund.amount, refund.currency),
            refund.reason,
            status_badge,
            assignee.assigned_to.username if assignee else "—",
            refund.created_at.strftime("%Y-%m-%d %H:%M"),
            action,
        ]


class RefundDetailView(AppAccessRequiredMixin, DetailView):
    """Refund detail with actions, notes, and activity history."""

    app_key = "refunds"
    model = RefundRequest
    template_name = "refunds/detail.html"
    context_object_name = "refund"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        refund = context["refund"]
        user = self.request.user
        context["page_title"] = f"Refund #{refund.pk}"
        context["breadcrumbs"] = app_breadcrumbs(
            app_key="refunds",
            object_label=f"Refund #{refund.pk}",
        )
        context["current_assignment"] = RefundService().get_current_assignment(refund)
        context["activity"] = RefundService().get_activity(refund)
        context["notes"] = RefundService().get_notes(refund)
        context["can_approve"] = can_perform_action(user, "refunds", "approve")
        context["can_reject"] = can_perform_action(user, "refunds", "reject")
        context["can_assign"] = can_perform_action(user, "refunds", "assign")
        context["is_terminal"] = refund.status in (
            RefundRequest.Status.APPROVED,
            RefundRequest.Status.REJECTED,
        )
        context["status_badge_style"] = _badge_style(refund.status)
        context["reject_form"] = RefundRejectForm()
        context["assign_form"] = RefundAssignForm()
        context["note_form"] = RefundNoteForm()
        return context


class RefundApproveView(AppActionRequiredMixin, View):
    """Approve a refund."""

    app_key = "refunds"
    action_key = "approve"

    def post(self, request, pk):
        refund = get_object_or_404(RefundRequest, pk=pk)
        try:
            RefundService().approve(refund, request.user)
            messages.success(request, "Refund approved.")
        except RefundServiceError as exc:
            messages.error(request, str(exc))
        return redirect(reverse("refunds:detail", args=[pk]))


class RefundRejectView(AppActionRequiredMixin, View):
    """Reject a refund with a reason."""

    app_key = "refunds"
    action_key = "reject"

    def post(self, request, pk):
        refund = get_object_or_404(RefundRequest, pk=pk)
        form = RefundRejectForm(request.POST)
        if form.is_valid():
            try:
                RefundService().reject(refund, request.user, form.cleaned_data["reason"])
                messages.success(request, "Refund rejected.")
            except RefundServiceError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Please provide a rejection reason.")
        return redirect(reverse("refunds:detail", args=[pk]))


class RefundAssignView(AppActionRequiredMixin, View):
    """Assign a refund to a user."""

    app_key = "refunds"
    action_key = "assign"

    def post(self, request, pk):
        refund = get_object_or_404(RefundRequest, pk=pk)
        form = RefundAssignForm(request.POST)
        if form.is_valid():
            try:
                RefundService().assign(
                    refund,
                    form.cleaned_data["assigned_to"],
                    request.user,
                )
                messages.success(request, "Refund assigned.")
            except RefundServiceError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Please select a user to assign.")
        return redirect(reverse("refunds:detail", args=[pk]))


class RefundNoteView(AppAccessRequiredMixin, View):
    """Add a note to a refund."""

    app_key = "refunds"

    def post(self, request, pk):
        refund = get_object_or_404(RefundRequest, pk=pk)
        form = RefundNoteForm(request.POST)
        if form.is_valid():
            try:
                RefundService().add_note(refund, request.user, form.cleaned_data["body"])
                messages.success(request, "Note added.")
            except RefundServiceError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Please enter a note.")
        return redirect(reverse("refunds:detail", args=[pk]))


def _badge_style(status: str) -> str:
    return {
        RefundRequest.Status.PENDING: "warning",
        RefundRequest.Status.UNDER_REVIEW: "info",
        RefundRequest.Status.APPROVED: "success",
        RefundRequest.Status.REJECTED: "danger",
    }.get(status, "secondary")


def _current_assignment_map(refund_ids):
    return assignments.latest_map_for(RefundRequest, object_ids=refund_ids)
