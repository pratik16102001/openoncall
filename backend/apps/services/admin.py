from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "escalation_policy", "integration_key")
    list_filter = ("team",)
    readonly_fields = ("integration_key",)
