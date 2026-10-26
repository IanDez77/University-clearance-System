from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import ClearanceRequest, Faculty, Office, OfficeApproval


class ClearanceFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def login(self, username):
        self.client.logout()
        self.assertTrue(self.client.login(username=username, password="demo1234"))

    def choose_faculty(self, code):
        self.client.post(
            reverse("clearance:choose_faculty"), {"faculty": Faculty.objects.get(code=code).pk}
        )

    def request_clearance(self, username="student1", faculty="SOB"):
        self.login(username)
        self.choose_faculty(faculty)
        self.client.post(reverse("clearance:submit_request"))
        return ClearanceRequest.objects.get(student__username=username)

    def test_login_required(self):
        r = self.client.get(reverse("clearance:student_dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(reverse("clearance:login")))

    def test_own_login_and_logout_work(self):
        self.assertEqual(self.client.get(reverse("clearance:login")).status_code, 200)
        r = self.client.post(
            reverse("clearance:login"), {"username": "student1", "password": "demo1234"}
        )
        self.assertRedirects(r, reverse("clearance:home"), fetch_redirect_response=False)
        r = self.client.post(reverse("clearance:logout"))
        self.assertRedirects(r, reverse("clearance:login"), fetch_redirect_response=False)

    def test_everything_lives_under_clearance_prefix(self):
        self.assertTrue(reverse("clearance:home").startswith("/clearance/"))
        self.assertNotEqual(reverse("clearance:home"), "/")

    def test_home_redirects_by_role(self):
        self.login("student1")
        self.assertRedirects(self.client.get(reverse("clearance:home")), reverse("clearance:student_dashboard"))
        self.login("library")
        self.assertRedirects(self.client.get(reverse("clearance:home")), reverse("clearance:office_queue"))

    def test_roles_are_enforced(self):
        self.login("student1")
        self.assertEqual(self.client.get(reverse("clearance:office_queue")).status_code, 403)
        self.login("library")
        self.assertEqual(self.client.get(reverse("clearance:student_dashboard")).status_code, 403)

    def test_four_faculties_exist_and_are_selectable(self):
        self.login("student1")
        r = self.client.get(reverse("clearance:student_dashboard"))
        for code in ("SOB", "SOT", "SOEAS", "PTTI"):
            self.assertContains(r, code)

    def test_cannot_request_without_faculty(self):
        self.login("student1")
        self.client.post(reverse("clearance:submit_request"))
        self.assertFalse(ClearanceRequest.objects.filter(student__username="student1").exists())

    def test_invalid_faculty_is_rejected(self):
        self.login("student1")
        self.client.post(reverse("clearance:choose_faculty"), {"faculty": 9999})
        self.assertIsNone(
            self.client.get(reverse("clearance:student_dashboard")).context["faculty"]
        )

    def test_request_goes_to_general_offices_and_own_faculty_only(self):
        for username, code in (("student1", "SOB"), ("student2", "SOT"), ("student3", "SOEAS")):
            req = self.request_clearance(username, code)
            names = set(req.approvals.values_list("office__name", flat=True))
            self.assertEqual(
                names,
                {"Library", "Finance", "Hostels", "ICT", f"{code} Faculty Office"},
            )
            self.assertEqual(req.approvals.count(), 5)

    def test_second_submit_does_not_duplicate(self):
        self.request_clearance("student1", "SOB")
        self.client.post(reverse("clearance:submit_request"))
        self.assertEqual(
            ClearanceRequest.objects.filter(student__username="student1").count(), 1
        )

    def test_faculty_locked_after_request(self):
        self.request_clearance("student1", "SOB")
        self.choose_faculty("SOT")
        self.assertEqual(
            self.client.get(reverse("clearance:student_dashboard")).context["faculty"].code, "SOB"
        )

    def test_faculty_office_sees_only_its_own_faculty_students(self):
        self.request_clearance("student1", "SOB")
        self.request_clearance("student2", "SOT")
        self.login("sob")
        r = self.client.get(reverse("clearance:office_queue"))
        self.assertContains(r, "Student 1")
        self.assertNotContains(r, "Student 2")

    def test_faculty_office_cannot_decide_for_other_faculty(self):
        req = self.request_clearance("student2", "SOT")
        sot = OfficeApproval.objects.get(request=req, office__name="SOT Faculty Office")
        self.login("sob")
        r = self.client.post(reverse("clearance:decide", args=[sot.pk]), {"action": "approve"})
        self.assertEqual(r.status_code, 404)

    def test_full_flow_reject_resubmit_and_certificate(self):
        req = self.request_clearance("student1", "SOB")

        # every office approves except library, which rejects
        for office in Office.objects.filter(approvals__request=req):
            self.login(office.name.split()[0].lower())
            a = OfficeApproval.objects.get(request=req, office=office)
            if office.name == "Library":
                self.client.post(reverse("clearance:decide", args=[a.pk]), {"action": "reject", "comment": ""})
                a.refresh_from_db()
                self.assertEqual(a.status, OfficeApproval.PENDING)
                self.client.post(reverse("clearance:decide", args=[a.pk]), {"action": "reject", "comment": "Return 2 books"})
                a.refresh_from_db()
                self.assertEqual(a.status, OfficeApproval.REJECTED)
            else:
                self.client.post(reverse("clearance:decide", args=[a.pk]), {"action": "approve"})

        self.assertFalse(req.is_cleared)
        self.assertTrue(req.has_rejection)
        self.assertEqual(req.approved_count, 4)

        self.login("student1")
        self.assertRedirects(
            self.client.get(reverse("clearance:certificate", args=[req.pk])),
            reverse("clearance:home"),
            fetch_redirect_response=False,
        )

        lib = OfficeApproval.objects.get(request=req, office__name="Library")
        self.client.post(reverse("clearance:resubmit", args=[lib.pk]))
        lib.refresh_from_db()
        self.assertEqual(lib.status, OfficeApproval.PENDING)
        self.login("library")
        self.client.post(reverse("clearance:decide", args=[lib.pk]), {"action": "approve"})

        req = ClearanceRequest.objects.get(pk=req.pk)
        self.assertTrue(req.is_cleared)
        self.assertEqual(req.percent, 100)

        self.login("student1")
        r = self.client.get(reverse("clearance:certificate", args=[req.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, req.code)
        self.assertContains(r, "SOB")

    def test_office_cannot_decide_for_another_office(self):
        req = self.request_clearance("student1", "SOB")
        finance = OfficeApproval.objects.get(request=req, office__name="Finance")
        self.login("library")
        r = self.client.post(reverse("clearance:decide", args=[finance.pk]), {"action": "approve"})
        self.assertEqual(r.status_code, 404)

    def test_other_student_cannot_view_certificate(self):
        req = self.request_clearance("student1", "SOB")
        self.login("student2")
        self.assertEqual(self.client.get(reverse("clearance:certificate", args=[req.pk])).status_code, 403)


# --- Simulates a host site like the user's: its own "home" at "/" ---
from django.http import HttpResponse
from django.test import override_settings
from django.urls import include, path


def host_home(request):
    return HttpResponse("HOST LANDING PAGE")


urlpatterns = [
    path("", host_home, name="home"),
    path("clearance/", include("clearance_system.urls")),
]


@override_settings(ROOT_URLCONF=__name__)
class HostSiteCompatibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_host_landing_page_and_home_name_are_untouched(self):
        self.assertEqual(reverse("home"), "/")
        self.assertContains(self.client.get("/"), "HOST LANDING PAGE")

    def test_clearance_still_works_alongside_host(self):
        self.assertEqual(reverse("clearance:home"), "/clearance/")
        self.assertTrue(self.client.login(username="student1", password="demo1234"))
        r = self.client.get("/clearance/")
        self.assertRedirects(r, "/clearance/student/")
        self.assertEqual(self.client.get("/clearance/student/").status_code, 200)

    def test_logged_out_user_goes_to_clearance_login_not_host_login(self):
        r = self.client.get("/clearance/student/")
        self.assertTrue(r.url.startswith("/clearance/login/"))


class EmailNotificationTests(TestCase):
    """Emails go to the right people and never break the workflow."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def login(self, username):
        self.client.logout()
        self.assertTrue(self.client.login(username=username, password="demo1234"))

    def submit(self):
        self.login("student1")
        self.client.post(
            reverse("clearance:choose_faculty"),
            {"faculty": Faculty.objects.get(code="SOB").pk},
        )
        self.client.post(reverse("clearance:submit_request"))
        return ClearanceRequest.objects.get(student__username="student1")

    def decide(self, username, action, comment=""):
        clearance = ClearanceRequest.objects.get(student__username="student1")
        self.login(username)
        approval = clearance.approvals.get(office__staff__user__username=username)
        self.client.post(
            reverse("clearance:decide", args=[approval.pk]),
            {"action": action, "comment": comment},
        )
        return approval

    def recipients(self):
        from django.core import mail

        return sorted(addr for m in mail.outbox for addr in m.to)

    def test_submit_emails_student_and_all_five_offices(self):
        from django.core import mail

        clearance = self.submit()
        self.assertEqual(len(mail.outbox), 6)
        self.assertEqual(
            self.recipients(),
            sorted(
                ["student1@example.com", "library@example.com", "finance@example.com",
                 "hostels@example.com", "ict@example.com", "sob@example.com"]
            ),
        )
        receipt = [m for m in mail.outbox if m.to == ["student1@example.com"]][0]
        self.assertIn(clearance.code, receipt.subject)
        self.assertIn("http://testserver/clearance/student/", receipt.body)
        # Other faculties' offices are not told.
        self.assertNotIn("sot@example.com", self.recipients())

    def test_rejection_emails_student_with_reason(self):
        from django.core import mail

        self.submit()
        mail.outbox.clear()
        self.decide("library", "reject", "Return 2 books")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["student1@example.com"])
        self.assertIn("rejected", mail.outbox[0].subject)
        self.assertIn("Return 2 books", mail.outbox[0].body)

    def test_approval_emails_progress(self):
        from django.core import mail

        self.submit()
        mail.outbox.clear()
        self.decide("finance", "approve")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("1 of 5", mail.outbox[0].body)

    def test_final_approval_sends_certificate_email(self):
        from django.core import mail

        clearance = self.submit()
        for user in ("library", "finance", "hostels", "ict"):
            self.decide(user, "approve")
        mail.outbox.clear()
        self.decide("sob", "approve")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("fully cleared", mail.outbox[0].subject)
        self.assertIn(f"/clearance/certificate/{clearance.pk}/", mail.outbox[0].body)

    def test_resubmit_emails_the_office(self):
        from django.core import mail

        self.submit()
        approval = self.decide("library", "reject", "Return 2 books")
        mail.outbox.clear()
        self.login("student1")
        self.client.post(reverse("clearance:resubmit", args=[approval.pk]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["library@example.com"])

    def test_users_without_email_are_skipped_quietly(self):
        from django.core import mail
        from django.contrib.auth import get_user_model

        get_user_model().objects.filter(username="student1").update(email="")
        self.submit()
        self.assertNotIn("student1@example.com", self.recipients())
        self.assertEqual(len(mail.outbox), 5)

    def test_mail_server_failure_does_not_break_the_workflow(self):
        from unittest import mock

        with mock.patch(
            "clearance_system.notifications.send_mail", side_effect=OSError("smtp down")
        ):
            clearance = self.submit()
            self.decide("library", "approve")
        self.assertEqual(clearance.approvals.filter(status="approved").count(), 1)