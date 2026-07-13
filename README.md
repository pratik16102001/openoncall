# OpenOnCall

[![CI](https://github.com/pratik16102001/openoncall/actions/workflows/ci.yml/badge.svg)](https://github.com/pratik16102001/openoncall/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)

A self-hosted, open-source incident coordination and on-call paging platform. It ingests alerts from external monitoring tools (Prometheus Alertmanager, Datadog, CloudWatch, Sentry, or a generic webhook), pages the correct on-call responder via an escalation policy, tracks the full incident timeline automatically, and generates a postmortem draft on resolution.

OpenOnCall does **not** do monitoring/metrics itself — point your existing monitoring at it, it handles paging and incident coordination from there.

Licensed under the [MIT License](LICENSE). Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). Found a security issue? See [SECURITY.md](SECURITY.md) rather than opening a public issue.

## Quickstart (~5 minutes)

Requires Docker and Docker Compose.

```bash
git clone <this-repo-url> openoncall
cd openoncall
cp .env.example .env
docker compose up -d --build
```

Wait for the stack to come up (`docker compose ps` — `db`, `redis`, and `web` should show healthy), then:

```bash
docker compose exec web python manage.py createsuperuser
```

Follow the prompts (email + password), then open **http://localhost** and log in. You'll land on a "create your first team" screen — everything else (schedules, escalation policies, services) belongs to a team.

To send yourself a test alert once you've created a service (Services page → New service), copy its generic webhook URL and:

```bash
curl -X POST <generic-webhook-url> \
  -H "Content-Type: application/json" \
  -d '{"external_id":"test-1","title":"Test alert","severity":"warning","status":"firing"}'
```

The incident should appear on the dashboard within a few seconds.

## What's running

| Service | Purpose | Port |
|---|---|---|
| `web` | Django/DRF API (gunicorn) | 8000 |
| `worker` | Celery worker — escalation engine + notification delivery | — |
| `beat` | Celery beat scheduler | — |
| `db` | PostgreSQL 16 | 5432 |
| `redis` | Redis 7 — Celery broker/backend | 6379 |
| `frontend` | React SPA (nginx) | 80 |

Django admin is available at `http://localhost:8000/admin/` with the superuser account above — useful for inspecting data directly, though day-to-day use should go through the web UI at `http://localhost`.

## Configuring notification providers

Alerting works out of the box (incidents get created and timed out through escalation steps), but actually *notifying* someone needs provider credentials in `.env`, all bring-your-own-account — OpenOnCall never proxies notification costs through a shared account:

- **Slack**: each *team* configures its own Incoming Webhook URL from the dashboard (Team settings), not via `.env` — different teams may use different Slack workspaces. `SLACK_SIGNING_SECRET` in `.env` is instance-wide and only needed for the interactive "Acknowledge" button in Slack messages (from your Slack App's Basic Information → Signing Secret).
- **SMS / Voice**: set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` in `.env`.
- **Web Push**: set `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_ADMIN_EMAIL` in `.env` (generate a VAPID keypair with `python -m pywebpush.vapid` or any standard VAPID key generator).

See `.env.example` for the full list, with comments on each variable.

## Migrating from Grafana OnCall

```bash
docker compose exec web python manage.py import_grafana_oncall <export.json> --team <team-slug>
```

See `backend/apps/schedules/grafana_import.py` for the expected export JSON shape and the (clearly logged) simplifications made where OpenOnCall's model is less expressive than Grafana OnCall's.

## Before deploying for real

The `.env.example` defaults get you a working local instance, not a hardened public one. Before exposing this beyond your own machine:

- Set `SECRET_KEY` to a long random value (`.env.example`'s placeholder is not one).
- Set `DEBUG=False` (already the `.env.example` default) and set `ALLOWED_HOSTS` to your real domain.
- Terminate TLS in front of this stack (a reverse proxy, load balancer, or Caddy/nginx with a cert) — Docker Compose here is a self-hosted *reference* deployment and doesn't include HTTPS termination. Once you have it, also set Django's `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, and `CSRF_COOKIE_SECURE` to `True`.
- Run `docker compose exec web python manage.py check --deploy` — it'll flag anything above you missed.

## Development

For local development with hot-reload (bind-mounted source, Vite dev server instead of the nginx-served production build):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Backend tests:

```bash
docker compose exec web pytest
```

Frontend tests:

```bash
cd frontend && npm install && npm run test
```

## Repository layout

```
openoncall/
├── backend/            # Django/DRF API, Celery tasks
│   ├── apps/           # accounts, schedules, escalation, services, alerts, incidents, notifications
│   └── tests/          # pytest suite
├── frontend/           # React 18 + Vite + TypeScript SPA
├── docker-compose.yml       # self-hosted reference deployment
└── docker-compose.dev.yml   # local-dev overlay (hot reload)
```

## Scope (v1)

**In scope:** teams and on-call schedules with rotation + overrides, escalation policies, services with webhook integrations, alert ingestion from 5 sources, full incident lifecycle with automatic timeline, multi-channel notifications (Slack, SMS, voice, web push) with fallback on timeout, runbooks, postmortem export, a Grafana OnCall migration helper.

**Explicitly out of scope for v1:** monitoring/metrics ingestion, public status pages, native mobile apps, SSO/SAML, AI-generated summaries, multi-region deployment.

## Contributing

Bug reports, feature requests, and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for
dev setup, coding conventions, and the areas of the codebase where test coverage is non-negotiable
(escalation timing, notification fallback, dedup, team-scoping, schedule timezone/DST correctness — see
why in [CONTRIBUTING.md](CONTRIBUTING.md#tests)).

Release history is in [CHANGELOG.md](CHANGELOG.md).
