import secrets

from django.conf import settings
from django.db import models


def make_code():
    return "CLR-" + secrets.token_hex(4).upper()


class Faculty(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ["code"]
        verbose_name_plural = "faculties"

    def __str__(self):
        return self.code if self.name == self.code else f"{self.code} - {self.name}"


class Office(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    faculty = models.ForeignKey(
        Faculty,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="offices",
        help_text="Leave empty for offices every student must clear. "
        "Set it for a faculty office that only that faculty's students clear.",
    )

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Profile(models.Model):
    STUDENT = "student"
    OFFICE = "office"
    ROLE_CHOICES = [(STUDENT, "Student"), (OFFICE, "Office staff")]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=STUDENT)
    office = models.ForeignKey(
        Office,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff",
        help_text="Only for office staff.",
    )
    reg_number = models.CharField("Registration number", max_length=30, blank=True)
    faculty = models.ForeignKey(
        Faculty,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="students",
        help_text="The student's faculty. Students choose this themselves.",
    )

    def __str__(self):
        return f"{self.user.get_username()} ({self.get_role_display()})"


class ClearanceRequest(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clearance_requests",
    )
    code = models.CharField(max_length=20, unique=True, default=make_code, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.student.get_username()}"

    @property
    def total(self):
        return self.approvals.count()

    @property
    def approved_count(self):
        return self.approvals.filter(status=OfficeApproval.APPROVED).count()

    @property
    def percent(self):
        return int(self.approved_count * 100 / self.total) if self.total else 0

    @property
    def is_cleared(self):
        return self.total > 0 and self.approved_count == self.total

    @property
    def has_rejection(self):
        return self.approvals.filter(status=OfficeApproval.REJECTED).exists()


class OfficeApproval(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    request = models.ForeignKey(
        ClearanceRequest, on_delete=models.CASCADE, related_name="approvals"
    )
    office = models.ForeignKey(
        Office, on_delete=models.CASCADE, related_name="approvals"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    comment = models.CharField(max_length=300, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["office__order", "office__name"]
        unique_together = [("request", "office")]

    def __str__(self):
        return f"{self.request.code} / {self.office.name}: {self.status}"
