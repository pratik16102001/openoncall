## What does this change?

<!-- One or two sentences. Link the issue this addresses, if any (Fixes #...). -->

## Why?

<!-- The motivation -- what problem this solves or what it enables. -->

## How was this tested?

<!-- Automated tests added/updated, and/or manual verification steps. -->

## Checklist

- [ ] `docker compose exec web pytest` passes
- [ ] `cd frontend && npx tsc -b && npm run lint && npm run test` passes (if frontend changed)
- [ ] Added/updated tests for the change, especially if it touches escalation timing, notification
      fallback, acknowledge/halt behavior, alert dedup, team-scoping, or schedule rotation/timezone
      logic (see [CONTRIBUTING.md](../CONTRIBUTING.md#tests))
- [ ] Updated `.env.example` if this adds/changes an environment variable
- [ ] Updated `CHANGELOG.md` under `[Unreleased]`
