from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from clearance_system.models import Faculty, Office, Profile

# Offices every student must clear.
GENERAL_OFFICES = [
    ("Library", "Return all borrowed books and pay any fines"),
    ("Finance", "Fee balance must be cleared"),
    ("Hostels", "Room keys returned and no damages"),
    ("ICT", "University email and equipment returned"),
]

# Full names can be edited later in /admin/ (Faculties).
FACULTIES = ["SOB", "SOT", "SOEAS", "PTTI"]

DEMO_PASSWORD = "demo1234"


class Command(BaseCommand):
    help = "Create demo faculties, offices, office staff, students and an admin account."

    def make_staff(self, username, office):
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        Profile.objects.update_or_create(
            user=user, defaults={"role": Profile.OFFICE, "office": office}
        )

    def handle(self, *args, **options):
        faculties = {}
        for code in FACULTIES:
            faculties[code], _ = Faculty.objects.get_or_create(
                code=code, defaults={"name": code}
            )

        order = 0
        for name, desc in GENERAL_OFFICES:
            order += 1
            office, _ = Office.objects.get_or_create(
                name=name, defaults={"description": desc, "order": order}
            )
            self.make_staff(name.lower(), office)

        for code, faculty in faculties.items():
            order += 1
            office, _ = Office.objects.get_or_create(
                name=f"{code} Faculty Office",
                defaults={
                    "description": f"Clearance for {code} students",
                    "order": order,
                    "faculty": faculty,
                },
            )
            self.make_staff(code.lower(), office)

        # Students start without a faculty; they choose it on their dashboard.
        for n in (1, 2, 3):
            user, created = User.objects.get_or_create(
                username=f"student{n}",
                defaults={"first_name": "Student", "last_name": str(n)},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            Profile.objects.update_or_create(
                user=user,
                defaults={"role": Profile.STUDENT, "reg_number": f"S00{n}/2026"},
            )

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", DEMO_PASSWORD)

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write(f"Password for every demo account: {DEMO_PASSWORD}")
        self.stdout.write("Students: student1, student2, student3")
        self.stdout.write("General offices: library, finance, hostels, ict")
        self.stdout.write("Faculty offices: sob, sot, soeas, ptti")
        self.stdout.write("Admin: admin (use /admin/)")
