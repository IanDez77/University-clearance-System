from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from django.db.models import Q

from . import notifications
from .models import ClearanceRequest, Faculty, Office, OfficeApproval, Profile


LOGIN_URL = reverse_lazy("clearance:login")


def role_required(role):
    """Allow only logged-in users whose profile has the given role."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            profile = getattr(request.user, "profile", None)
            if profile is None or profile.role != role:
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return login_required(wrapper, login_url=LOGIN_URL)

    return decorator


@login_required(login_url=LOGIN_URL)
def home(request):
    profile = getattr(request.user, "profile", None)
    if profile and profile.role == Profile.STUDENT:
        return redirect("clearance:student_dashboard")
    if profile and profile.role == Profile.OFFICE:
        return redirect("clearance:office_queue")
    if request.user.is_staff:
        return redirect("admin:index")
    return HttpResponse(
        "Your account has no role yet. Ask an admin to set one.", status=403
    )


# ---------- Student ----------


@role_required(Profile.STUDENT)
def student_dashboard(request):
    clearance = request.user.clearance_requests.first()
    approvals = clearance.approvals.select_related("office") if clearance else []
    return render(
        request,
        "clearance_system/student_dashboard.html",
        {
            "clearance": clearance,
            "approvals": approvals,
            "faculties": Faculty.objects.all(),
            "faculty": request.user.profile.faculty,
        },
    )


@role_required(Profile.STUDENT)
@require_POST
def choose_faculty(request):
    # The faculty is locked once a clearance request exists.
    if request.user.clearance_requests.exists():
        messages.error(request, "You cannot change faculty after requesting clearance.")
        return redirect("clearance:student_dashboard")
    faculty = Faculty.objects.filter(pk=request.POST.get("faculty")).first()
    if faculty is None:
        messages.error(request, "Please choose your faculty.")
        return redirect("clearance:student_dashboard")
    profile = request.user.profile
    profile.faculty = faculty
    profile.save(update_fields=["faculty"])
    messages.success(request, f"Faculty set to {faculty.code}.")
    return redirect("clearance:student_dashboard")


@role_required(Profile.STUDENT)
@require_POST
def submit_request(request):
    if request.user.clearance_requests.exists():
        messages.info(request, "You already have a clearance request.")
        return redirect("clearance:student_dashboard")
    faculty = request.user.profile.faculty
    if faculty is None:
        messages.error(request, "Choose your faculty before requesting clearance.")
        return redirect("clearance:student_dashboard")
    # General offices (no faculty) plus the office of the student's own faculty.
    offices = Office.objects.filter(Q(faculty__isnull=True) | Q(faculty=faculty))
    if not offices:
        messages.error(request, "No offices are set up yet. Contact the admin.")
        return redirect("clearance:student_dashboard")
    with transaction.atomic():
        clearance = ClearanceRequest.objects.create(student=request.user)
        OfficeApproval.objects.bulk_create(
            [OfficeApproval(request=clearance, office=o) for o in offices]
        )
    notifications.request_submitted(request, clearance)
    messages.success(request, "Clearance request submitted to all offices.")
    return redirect("clearance:student_dashboard")


@role_required(Profile.STUDENT)
@require_POST
def resubmit(request, pk):
    approval = get_object_or_404(
        OfficeApproval,
        pk=pk,
        request__student=request.user,
        status=OfficeApproval.REJECTED,
    )
    approval.status = OfficeApproval.PENDING
    approval.decided_by = None
    approval.decided_at = None
    approval.save()
    notifications.resubmitted(request, approval)
    messages.success(request, f"Sent back to {approval.office.name} for review.")
    return redirect("clearance:student_dashboard")


@login_required(login_url=LOGIN_URL)
def certificate(request, pk):
    clearance = get_object_or_404(ClearanceRequest, pk=pk)
    if clearance.student != request.user and not request.user.is_staff:
        raise PermissionDenied
    if not clearance.is_cleared:
        messages.error(request, "Certificate is available once every office approves.")
        return redirect("clearance:home")
    return render(
        request,
        "clearance_system/certificate.html",
        {"clearance": clearance, "approvals": clearance.approvals.select_related("office")},
    )


# ---------- Office staff ----------


@role_required(Profile.OFFICE)
def office_queue(request):
    office = request.user.profile.office
    if office is None:
        return HttpResponse("You are not assigned to an office. Ask an admin.", status=403)
    base = OfficeApproval.objects.filter(office=office).select_related(
        "request__student__profile"
    )
    pending = base.filter(status=OfficeApproval.PENDING).order_by("request__created_at")
    decided = base.exclude(status=OfficeApproval.PENDING).order_by("-decided_at")[:10]
    return render(
        request,
        "clearance_system/office_queue.html",
        {"office": office, "pending": pending, "decided": decided},
    )


@role_required(Profile.OFFICE)
@require_POST
def decide(request, pk):
    office = request.user.profile.office
    approval = get_object_or_404(OfficeApproval, pk=pk, office=office)
    action = request.POST.get("action")
    comment = request.POST.get("comment", "").strip()

    if action == "approve":
        approval.status = OfficeApproval.APPROVED
    elif action == "reject":
        if not comment:
            messages.error(request, "Please give a reason when rejecting.")
            return redirect("clearance:office_queue")
        approval.status = OfficeApproval.REJECTED
    else:
        raise PermissionDenied

    approval.comment = comment
    approval.decided_by = request.user
    approval.decided_at = timezone.now()
    approval.save()
    notifications.decision_made(request, approval)
    messages.success(request, f"Request {approval.request.code} {approval.status}.")
    return redirect("clearance:office_queue")