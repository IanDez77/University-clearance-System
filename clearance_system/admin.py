from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import ClearanceRequest, Faculty, Office, OfficeApproval, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("code", "name")


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ("name", "faculty", "order", "description")
    list_editable = ("order",)


class OfficeApprovalInline(admin.TabularInline):
    model = OfficeApproval
    extra = 0


@admin.register(ClearanceRequest)
class ClearanceRequestAdmin(admin.ModelAdmin):
    list_display = ("code", "student", "created_at")
    inlines = [OfficeApprovalInline]
