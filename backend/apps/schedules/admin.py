from django.contrib import admin

from .models import Schedule, ScheduleOverride, ScheduleParticipant


class ScheduleParticipantInline(admin.TabularInline):
    model = ScheduleParticipant
    extra = 1


class ScheduleOverrideInline(admin.TabularInline):
    model = ScheduleOverride
    extra = 0


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "rotation_type", "rotation_length_hours", "timezone")
    list_filter = ("team", "rotation_type")
    inlines = [ScheduleParticipantInline, ScheduleOverrideInline]


@admin.register(ScheduleOverride)
class ScheduleOverrideAdmin(admin.ModelAdmin):
    list_display = ("schedule", "user", "start_time", "end_time")
    list_filter = ("schedule",)
