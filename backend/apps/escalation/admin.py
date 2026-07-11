from django.contrib import admin

from .models import EscalationPolicy, EscalationStep


class EscalationStepInline(admin.TabularInline):
    model = EscalationStep
    extra = 1


@admin.register(EscalationPolicy)
class EscalationPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "repeat_count")
    list_filter = ("team",)
    inlines = [EscalationStepInline]


@admin.register(EscalationStep)
class EscalationStepAdmin(admin.ModelAdmin):
    list_display = ("policy", "order", "target_type", "target_id", "timeout_minutes")
    list_filter = ("policy", "target_type")
