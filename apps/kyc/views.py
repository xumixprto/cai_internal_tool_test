"""KYC app views."""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.html import format_html
from django.views import View
from django.views.generic import DetailView, ListView

from apps.kyc.forms import (
    KYCAssignForm,
    KYCEscalateForm,
    KYCFilterForm,
    KYCNoteForm,
    KYCRejectForm,
)
from apps.kyc.models.kyc import KYCApplication
from apps.kyc.services.kyc import KYCService, KYCServiceError
from core.navigation.breadcrumbs import app_breadcrumbs
from core.rbac.mixins import AppAccessRequiredMixin, AppActionRequiredMixin
from core.rbac.services import can_perform_action
from shared.services.primitives import assignments


class KYCQueueView(AppAccessRequiredMixin, ListView):
    """Operational KYC review queue with filters and pagination."""

    app_key = "kyc"
    model = KYCApplication
    template_name = "kyc/queue.html"
    context_object_name = "kyc_cases"
    paginate_by = 10

    def get_queryset(self):
        qs = KYCApplication.objects.order_by("-created_at")
        self.filter_form = KYCFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            data = self.filter_form.cleaned_data
            if data.get("status"):
                qs = qs.filter(status=data["status"])
            if data.get("risk"):
                qs = qs.filter(risk_level=data["risk"])
            if data.get("verification"):
                qs = qs.filter(provider_verification_status=data["verification"])
            search = (data.get("q") or "").strip()
            if search:
                qs = qs.filter(
                    Q(customer_name__icontains=search)
                    | Q(customer_identifier__icontains=search)
                    | Q(country__icontains=search)
                    | Q(document_identifier__icontains=search)
                )
            assigned_to = data.get("assigned_to")
            if assigned_to:
                qs = self._filter_by_current_assignee(qs, assigned_to)
        return qs

    def _filter_by_current_assignee(self, qs, assigned_to):
        return qs.filter(pk__in=assignments.currently_assigned_to(KYCApplication, assigned_to))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = getattr(self, "filter_form", KYCFilterForm(self.request.GET))
        get_copy = self.request.GET.copy()
        get_copy.pop("page", None)
        context["extra_params"] = "&" + get_copy.urlencode() if get_copy else ""
        context["page_title"] = "KYC Review"
        cases = list(context["kyc_cases"])
        context["current_assignments"] = _current_assignment_map([c.pk for c in cases])
        context["table_headers"] = [
            "Customer",
            "Country",
            "Risk",
            "Verification",
            "Flags",
            "Status",
            "Assigned To",
            "Submitted",
        ]
        context["table_rows"] = [
            self._build_table_row(case, context["current_assignments"]) for case in cases
        ]
        context["safe"] = True
        context["action_column"] = True
        return context

    def _build_table_row(self, case, current_assignments):
        assignee = current_assignments.get(case.pk)
        detail_url = reverse("kyc:detail", args=[case.pk])
        action = format_html(
            '<a class="btn btn-sm btn-outline-primary" href="{0}">View</a>',
            detail_url,
        )
        status_badge = format_html(
            '<span class="badge rounded-pill bg-{0}">{1}</span>',
            _badge_style(case.status),
            case.get_status_display(),
        )
        risk_badge = format_html(
            '<span class="badge rounded-pill bg-{0}">{1}</span>',
            _risk_badge_style(case.risk_level),
            case.get_risk_level_display(),
        )
        verification_badge = format_html(
            '<span class="badge rounded-pill bg-{0}">{1}</span>',
            _verification_badge_style(case.provider_verification_status),
            case.get_provider_verification_status_display(),
        )
        return [
            format_html(
                "<strong>{0}</strong><br><small class='text-muted'>{1}</small>",
                case.customer_name,
                case.customer_identifier,
            ),
            case.country,
            risk_badge,
            verification_badge,
            case.screening_flags or "—",
            status_badge,
            assignee.assigned_to.username if assignee else "—",
            case.created_at.strftime("%Y-%m-%d %H:%M"),
            action,
        ]


class KYCDetailView(AppAccessRequiredMixin, DetailView):
    """KYC detail with actions, notes, and activity history."""

    app_key = "kyc"
    model = KYCApplication
    template_name = "kyc/detail.html"
    context_object_name = "case"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        case = context["case"]
        user = self.request.user
        context["page_title"] = f"KYC #{case.pk}"
        context["breadcrumbs"] = app_breadcrumbs(
            app_key="kyc",
            object_label=f"KYC #{case.pk}",
        )
        context["current_assignment"] = KYCService().get_current_assignment(case)
        context["activity"] = KYCService().get_activity(case)
        context["notes"] = KYCService().get_notes(case)
        can_approve = can_perform_action(user, "kyc", "approve")
        can_reject = can_perform_action(user, "kyc", "reject")
        can_escalate = can_perform_action(user, "kyc", "escalate")
        can_assign = can_perform_action(user, "kyc", "assign")
        context["can_approve"] = can_approve
        context["can_reject"] = can_reject
        context["can_escalate"] = can_escalate
        context["can_assign"] = can_assign
        context["can_start_review"] = case.status == KYCApplication.Status.PENDING
        context["can_return_to_review"] = case.status == KYCApplication.Status.ESCALATED
        context["can_approve_action"] = (
            can_approve and case.status == KYCApplication.Status.UNDER_REVIEW
        )
        context["can_reject_action"] = can_reject and case.status in (
            KYCApplication.Status.PENDING,
            KYCApplication.Status.UNDER_REVIEW,
        )
        context["can_escalate_action"] = (
            can_escalate and case.status == KYCApplication.Status.UNDER_REVIEW
        )
        context["is_terminal"] = case.status in self._terminal_statuses()
        context["status_badge_style"] = _badge_style(case.status)
        context["risk_badge_style"] = _risk_badge_style(case.risk_level)
        context["verification_badge_style"] = _verification_badge_style(
            case.provider_verification_status
        )
        context["reject_form"] = KYCRejectForm()
        context["escalate_form"] = KYCEscalateForm()
        context["assign_form"] = KYCAssignForm()
        context["note_form"] = KYCNoteForm()
        return context

    @staticmethod
    def _terminal_statuses():
        return (KYCApplication.Status.APPROVED, KYCApplication.Status.REJECTED)


class KYCReviewView(AppAccessRequiredMixin, View):
    """Move a KYC case to under review (from pending or escalated)."""

    app_key = "kyc"

    def post(self, request, pk):
        case = get_object_or_404(KYCApplication, pk=pk)
        try:
            KYCService().move_to_under_review(case, request.user)
            messages.success(request, "KYC case is now under review.")
        except KYCServiceError as exc:
            messages.error(request, str(exc))
        return redirect(reverse("kyc:detail", args=[pk]))


class KYCApproveView(AppActionRequiredMixin, View):
    """Approve a KYC case."""

    app_key = "kyc"
    action_key = "approve"

    def post(self, request, pk):
        case = get_object_or_404(KYCApplication, pk=pk)
        try:
            KYCService().approve(case, request.user)
            messages.success(request, "KYC case approved.")
        except KYCServiceError as exc:
            messages.error(request, str(exc))
        return redirect(reverse("kyc:detail", args=[pk]))


class KYCRejectView(AppActionRequiredMixin, View):
    """Reject a KYC case with a reason."""

    app_key = "kyc"
    action_key = "reject"

    def post(self, request, pk):
        case = get_object_or_404(KYCApplication, pk=pk)
        form = KYCRejectForm(request.POST)
        if form.is_valid():
            try:
                KYCService().reject(case, request.user, form.cleaned_data["reason"])
                messages.success(request, "KYC case rejected.")
            except KYCServiceError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Please provide a rejection reason.")
        return redirect(reverse("kyc:detail", args=[pk]))


class KYCEscalateView(AppActionRequiredMixin, View):
    """Escalate a KYC case with a reason."""

    app_key = "kyc"
    action_key = "escalate"

    def post(self, request, pk):
        case = get_object_or_404(KYCApplication, pk=pk)
        form = KYCEscalateForm(request.POST)
        if form.is_valid():
            try:
                KYCService().escalate(case, request.user, form.cleaned_data["reason"])
                messages.success(request, "KYC case escalated.")
            except KYCServiceError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Please provide an escalation reason.")
        return redirect(reverse("kyc:detail", args=[pk]))


class KYCAssignView(AppActionRequiredMixin, View):
    """Assign a KYC case to a user."""

    app_key = "kyc"
    action_key = "assign"

    def post(self, request, pk):
        case = get_object_or_404(KYCApplication, pk=pk)
        form = KYCAssignForm(request.POST)
        if form.is_valid():
            try:
                KYCService().assign(
                    case,
                    form.cleaned_data["assigned_to"],
                    request.user,
                )
                messages.success(request, "KYC case assigned.")
            except KYCServiceError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Please select a user to assign.")
        return redirect(reverse("kyc:detail", args=[pk]))


class KYCNoteView(AppAccessRequiredMixin, View):
    """Add an internal note to a KYC case."""

    app_key = "kyc"

    def post(self, request, pk):
        case = get_object_or_404(KYCApplication, pk=pk)
        form = KYCNoteForm(request.POST)
        if form.is_valid():
            try:
                KYCService().add_note(case, request.user, form.cleaned_data["body"])
                messages.success(request, "Note added.")
            except KYCServiceError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Please enter a note.")
        return redirect(reverse("kyc:detail", args=[pk]))


def _badge_style(status: str) -> str:
    return {
        KYCApplication.Status.PENDING: "secondary",
        KYCApplication.Status.UNDER_REVIEW: "info",
        KYCApplication.Status.ESCALATED: "warning",
        KYCApplication.Status.APPROVED: "success",
        KYCApplication.Status.REJECTED: "danger",
    }.get(status, "secondary")


def _risk_badge_style(risk: str) -> str:
    return {
        KYCApplication.RiskLevel.LOW: "success",
        KYCApplication.RiskLevel.MEDIUM: "info",
        KYCApplication.RiskLevel.HIGH: "danger",
    }.get(risk, "secondary")


def _verification_badge_style(verification: str) -> str:
    return {
        KYCApplication.ProviderVerificationStatus.PENDING: "secondary",
        KYCApplication.ProviderVerificationStatus.VERIFIED: "success",
        KYCApplication.ProviderVerificationStatus.FAILED: "danger",
        KYCApplication.ProviderVerificationStatus.FLAGGED: "warning",
    }.get(verification, "secondary")


def _current_assignment_map(case_ids):
    return assignments.latest_map_for(KYCApplication, object_ids=case_ids)
