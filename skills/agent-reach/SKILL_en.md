# Agent Reach — companion reference

The canonical entry for this shared package is [SKILL.md](SKILL.md).
Use existing suitable connectors first; use Reach only to supply missing content.

## Current command contract

Read [current CLI](references/current-cli.md), based on the public Reach 1.6.0
skill. Run `agent-reach channels` for the installed version's actions and
parameters, then `agent-reach read <URL>` or the documented channel action.
Missing commands indicate a version difference; do not silently upgrade.

Successful results put fetched items in `items`. An excerpt, application shell,
comment count, or subtitle track list does not establish complete content.
Report what was actually retrieved. Read [capability scope](references/capabilities.md)
when judging completeness.

## Scope and sessions

Prefer ego Lite for browser work. Do not automatically start another browser,
copy browser sessions, install dependencies, or change accounts. User login and
verification happen in the official interface. Authentication, rate-limit,
platform-verification, or busy states stop that attempt.

This skill reads content. It does not post, comment, like, message, or contact
anyone. Never put credentials or private account state in shared files.

Platform-specific references linked from the canonical entry apply only to
those actual backends; their commands are not aliases for the current Reach CLI.
