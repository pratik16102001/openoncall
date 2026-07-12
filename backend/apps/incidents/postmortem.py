def generate_postmortem_markdown(incident):
    alert = incident.triggering_alert
    lines = [f"# Postmortem: {incident.title}", ""]

    lines.append(f"- **Service:** {incident.service.name}")
    lines.append(f"- **Severity:** {alert.severity}")
    lines.append(f"- **Status:** {incident.status}")
    lines.append(f"- **Triggered:** {incident.created_at.isoformat()}")
    if incident.acknowledged_at:
        lines.append(f"- **Acknowledged:** {incident.acknowledged_at.isoformat()}")
    if incident.resolved_at:
        lines.append(f"- **Resolved:** {incident.resolved_at.isoformat()}")
    if incident.assigned_to:
        lines.append(f"- **Assigned to:** {incident.assigned_to.email}")
    if incident.resolved_at:
        lines.append(f"- **Time to resolve:** {incident.resolved_at - incident.created_at}")

    lines += ["", "## Timeline", ""]
    for event in incident.timeline_events.order_by("created_at"):
        actor = event.actor.email if event.actor else "system"
        lines.append(
            f"- `{event.created_at.isoformat()}` **{event.get_event_type_display()}** ({actor}): "
            f"{event.message}"
        )

    if incident.service.runbook_url or incident.service.runbook_markdown:
        lines += ["", "## Runbook", ""]
        if incident.service.runbook_url:
            lines.append(f"[{incident.service.runbook_url}]({incident.service.runbook_url})")
        if incident.service.runbook_markdown:
            lines += ["", incident.service.runbook_markdown]

    return "\n".join(lines)
