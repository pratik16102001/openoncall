# Security Policy

## Supported Versions

OpenOnCall is pre-1.0. Security fixes are made against the `main` branch
only; there are no maintained release branches yet.

| Version | Supported |
|---|---|
| `main`  | :white_check_mark: |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, report it privately using one of these channels:

1. [GitHub Security Advisories](https://github.com/pratik16102001/openoncall/security/advisories/new)
   for this repository (preferred), or
2. Email **pratikvaishnani1610@gmail.com** with a description of the issue,
   steps to reproduce, and its potential impact.

You should receive an acknowledgment within a few days. We'll work with you
to understand and validate the issue, aim to ship a fix, and credit you in
the release notes (unless you'd prefer to stay anonymous).

## Scope Notes

OpenOnCall is self-hosted: operators run their own instance and supply their
own Twilio/Slack/VAPID credentials. A few things worth keeping in mind when
reporting:

- The `integration_key` embedded in webhook URLs (`/webhooks/<source>/<key>/`)
  acts as a bearer credential for alert ingestion into a specific service.
  Treat key leakage (e.g. via `raw_payload` logging, error messages, or
  server logs) as a real finding.
- The Slack interactivity endpoint verifies requests via HMAC signature
  (`SLACK_SIGNING_SECRET`); issues in that verification path are
  high-severity.
- Cross-team data isolation (a user from Team A reading/acting on Team B's
  resources) is a core safety property — see `apps/accounts/permissions.py`
  and the team-scoping tests. Any bypass is high-severity.
