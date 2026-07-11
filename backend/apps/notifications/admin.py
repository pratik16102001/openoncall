from django.contrib import admin

from .models import NotificationAttempt


@admin.register(NotificationAttempt)
class NotificationAttemptAdmin(admin.ModelAdmin):
    list_display = ("incident", "user", "channel", "status", "escalation_step", "created_at")
    list_filter = ("channel", "status")
    readonly_fields = ("provider_message_id", "error_message")
