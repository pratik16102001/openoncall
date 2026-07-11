from django.contrib import admin

from .models import Incident, TimelineEvent


class TimelineEventInline(admin.TabularInline):
    model = TimelineEvent
    extra = 0
    readonly_fields = ("event_type", "actor", "message", "metadata", "created_at")
    can_delete = False


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("title", "service", "status", "assigned_to", "created_at", "resolved_at")
    list_filter = ("status", "service")
    inlines = [TimelineEventInline]


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = ("incident", "event_type", "actor", "created_at")
    list_filter = ("event_type",)
