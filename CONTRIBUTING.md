# Contributing to OpenOnCall

Thanks for considering a contribution. This project pages people about
production incidents — correctness and test coverage matter more here than
in most side projects.

## Before you start

- For anything beyond a small fix, please open an issue first to discuss the
  approach. It's much easier to course-correct a proposal than a finished PR.
- Check open issues and PRs so you're not duplicating work.
- This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Development setup

See the [README](README.md#development) for the full dev workflow
(`docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d` gets
you a hot-reloading stack). In short:

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker compose exec web python manage.py createsuperuser
```

Backend tests: `docker compose exec web pytest`
Frontend tests: `cd frontend && npm install && npm run test`
Frontend typecheck/lint: `cd frontend && npx tsc -b && npm run lint`

## Making changes

- **Backend**: Django apps live under `backend/apps/`, one per domain concept
  (`accounts`, `schedules`, `escalation`, `services`, `alerts`, `incidents`,
  `notifications`). Business logic that's reused across entry points (the
  REST API, the Slack interactivity callback, Celery tasks) belongs in each
  app's `services.py`, not duplicated in views — see
  `apps/incidents/services.py` for the pattern.
- **Frontend**: pages in `frontend/src/pages/`, typed API calls in
  `frontend/src/api/` (one module per backend resource), shared UI in
  `frontend/src/components/`.
- Match the existing code style; there's no separate style guide beyond
  "look at the surrounding file."

## Tests

New behavior needs a test. This is especially non-negotiable for six areas,
since a silent regression in any of them means someone doesn't get paged
during a real incident:

1. Escalation timing and step progression
2. Notification fallback on missing contact info / provider failure
3. Acknowledge correctly halting escalation
4. Alert dedup / idempotency
5. Team-scoped permission isolation (a user from Team A must never read or
   act on Team B's data)
6. Timezone/DST correctness in schedule rotation

Look at `backend/tests/test_escalation_engine.py`,
`test_notifications.py`, `test_alert_ingestion.py`, `test_team_scoping.py`,
and `test_schedule_rotation.py` for the existing patterns before adding to
these areas.

## Commit messages and PRs

- Write commit messages that explain *why*, not just *what* — the diff
  already shows what changed.
- Keep PRs focused. A bug fix doesn't need to also refactor unrelated code.
- Make sure `pytest`, `tsc -b`, and `npm run lint` all pass before opening a
  PR — CI will run all three.
- Fill out the PR template; it's short on purpose.

## Reporting bugs / requesting features

Use the issue templates. For security vulnerabilities, see
[SECURITY.md](SECURITY.md) instead of opening a public issue.
