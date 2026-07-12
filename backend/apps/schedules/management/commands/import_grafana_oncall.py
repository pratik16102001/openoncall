import json

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Team
from apps.schedules.grafana_import import import_grafana_oncall_export


class Command(BaseCommand):
    help = (
        "Import a Grafana OnCall export (see apps/schedules/grafana_import.py "
        "for the expected JSON shape) into Schedule/EscalationPolicy objects "
        "for an existing OpenOnCall team."
    )

    def add_arguments(self, parser):
        parser.add_argument("export_path", help="Path to the Grafana OnCall export JSON file")
        parser.add_argument(
            "--team", required=True, help="Slug of the OpenOnCall team to import into"
        )

    def handle(self, *args, **options):
        team = Team.objects.filter(slug=options["team"]).first()
        if team is None:
            raise CommandError(f"No team with slug '{options['team']}'.")

        try:
            with open(options["export_path"]) as f:
                export_data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read export file: {exc}") from exc

        result = import_grafana_oncall_export(export_data, team)

        self.stdout.write(self.style.SUCCESS(f"Created {len(result.schedules_created)} schedule(s):"))
        for schedule in result.schedules_created:
            self.stdout.write(f"  - {schedule.name} ({schedule.schedule_participants.count()} participants)")

        self.stdout.write(
            self.style.SUCCESS(f"Created {len(result.escalation_policies_created)} escalation polic(y/ies):")
        )
        for policy in result.escalation_policies_created:
            self.stdout.write(f"  - {policy.name} ({policy.steps.count()} steps)")

        if result.warnings:
            self.stdout.write(self.style.WARNING(f"\n{len(result.warnings)} warning(s):"))
            for warning in result.warnings:
                self.stdout.write(self.style.WARNING(f"  - {warning}"))
