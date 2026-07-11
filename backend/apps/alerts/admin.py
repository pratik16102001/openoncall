from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("title", "service", "source", "severity", "status", "received_at")
    list_filter = ("source", "severity", "status", "service")
    readonly_fields = ("raw_payload",)
