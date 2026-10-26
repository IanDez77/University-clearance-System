"""Email notifications for the clearance workflow.

Every function here is safe to call from a view: a failed email is logged and
swallowed, so a mail-server problem never blocks a student or an office.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from .models import Profile

logger = logging.getLogger(__name__)

SUBJECT_PREFIX = "[University Clearance] "


def _send(subject, body, recipients):
    recipients = sorted({r for r in recipients if r})
    if not recipients:
        return 0
    try:
        return send_mail(
            SUBJECT_PREFIX + subject,
            body,
            getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipients,
            fail_silently=False,
        )
    except Exception:  # never let email break the workflow
        logger.exception("Could not send email %r to %s", subject, recipients)
        return 0


def _link(request, name, *args):
    return request.build_absolute_uri(reverse(f"clearance:{name}", args=args))


def _name(user):
    return user.get_full_name() or user.get_username()


def _office_emails(office):
    return [
        p.user.email
        for p in Profile.objects.filter(office=office, role=Profile.OFFICE).select_related("user")
        if p.user.email
    ]


def request_submitted(request, clearance):
    """Student gets a receipt; each office gets told there is a new request."""
    student = clearance.student
    approvals = list(clearance.approvals.select_related("office"))
    offices = ", ".join(a.office.name for a in approvals)
    _send(
        f"Request {clearance.code} received",
        f"Hello {_name(student)},\n\n"
        f"Your clearance request {clearance.code} has been sent to: {offices}.\n"
        f"Track its progress here:\n{_link(request, 'student_dashboard')}\n",
        [student.email],
    )
    for a in approvals:
        _send(
            f"New clearance request {clearance.code}",
            f"A new clearance request is waiting for {a.office.name}.\n\n"
            f"Student: {_name(student)} ({student.profile.reg_number or 'no reg. number'})\n"
            f"Review it here:\n{_link(request, 'office_queue')}\n",
            _office_emails(a.office),
        )


def decision_made(request, approval):
    """Tell the student what an office decided; special mail when fully cleared."""
    clearance = approval.request
    student = clearance.student
    office = approval.office.name
    if approval.status == approval.REJECTED:
        _send(
            f"{office} rejected your request",
            f"Hello {_name(student)},\n\n"
            f"{office} could not clear request {clearance.code}.\n"
            f"Reason: {approval.comment}\n\n"
            f"Fix the issue, then open your dashboard and press Resubmit:\n"
            f"{_link(request, 'student_dashboard')}\n",
            [student.email],
        )
    elif clearance.is_cleared:
        _send(
            f"You are fully cleared ({clearance.code})",
            f"Congratulations {_name(student)},\n\n"
            f"Every office has approved request {clearance.code}.\n"
            f"Your certificate is ready:\n{_link(request, 'certificate', clearance.pk)}\n",
            [student.email],
        )
    else:
        note = f"\nNote: {approval.comment}\n" if approval.comment else ""
        _send(
            f"{office} approved your request",
            f"Hello {_name(student)},\n\n"
            f"{office} has approved request {clearance.code}. "
            f"{clearance.approved_count} of {clearance.total} offices cleared.\n{note}\n"
            f"{_link(request, 'student_dashboard')}\n",
            [student.email],
        )


def resubmitted(request, approval):
    """Tell the office that a student fixed the problem and wants a re-check."""
    student = approval.request.student
    _send(
        f"Resubmitted: {approval.request.code}",
        f"{_name(student)} has resubmitted request {approval.request.code} "
        f"to {approval.office.name} after a rejection.\n"
        f"Review it here:\n{_link(request, 'office_queue')}\n",
        _office_emails(approval.office),
    )
