# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
once it reaches 1.0.

## [Unreleased]

### Added

- Initial implementation: teams, on-call schedules with rotation + manual
  overrides, escalation policies, services with per-source webhook
  integrations, alert ingestion (generic, Alertmanager, Datadog, CloudWatch,
  Sentry), full incident lifecycle with automatic timeline, multi-channel
  notifications (Slack with interactive acknowledgment, Twilio SMS/voice,
  Web Push) with timeout-based fallback, runbooks, postmortem markdown
  export, React dashboard, Grafana OnCall migration script, Docker Compose
  self-hosted deployment.

[Unreleased]: https://github.com/pratik16102001/openoncall/commits/main
