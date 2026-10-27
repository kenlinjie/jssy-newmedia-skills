# Data governance

## Allowed data

Use:

- The user's own writing, recordings, transcripts, and revisions.
- Materials whose owner explicitly authorized this use.
- Public benchmark material used only for structural comparison.
- Factual notes the user confirms may be stored in the profile.

Do not use:

- Leaked, private, or access-controlled third-party material without permission.
- Authentication secrets, tokens, passwords, or unnecessary sensitive identifiers.
- Private conversations whose participants did not authorize profile training.
- A public figure's work to create deceptive impersonation or false endorsement.

## Identity and benchmark separation

`corpus/approved/` answers: “What does this person demonstrably do?”

`corpus/benchmark/` answers: “What mechanism might be useful to study?”

A benchmark can inspire a hypothesis, but it cannot become an approved identity rule without evidence from the authorized personal corpus.

## Person-to-person isolation

- Require an explicit person label before ingestion; do not identify a speaker from voice similarity.
- Keep every person's corpus, facts, corrections, rules, eval results, and snapshots in a separate profile.
- When a newly named person has no profile and the user wants continued learning, create a new profile and person-specific skill.
- Never use another person's profile as a temporary inbox, even when the files will be moved later.

## Repository defaults

The generic skill repository may contain:

- Skill instructions.
- Empty schemas and examples invented for documentation.
- Deterministic scripts and tests.

It must not contain:

- A real person's profile.
- Raw or cleaned personal corpus.
- AI draft → human final corrections.
- Facts, blacklists, evaluation results, or snapshots from a real profile.

`init_profile.py` creates a profile-local `.gitignore` that ignores everything by default. If the user later wants to version a profile, review every tracked path and use a private repository unless they explicitly choose otherwise.

## Publish checklist

Before commit or upload:

1. Search for profile names, email addresses, phone numbers, access tokens, and source transcript phrases.
2. Confirm no `voice-profiles/`, `profiles/`, corpus, corrections, eval results, or snapshots are tracked.
3. Inspect `git diff --cached` rather than relying only on filenames.
4. Confirm examples are synthetic and do not quote a real source.
5. Confirm repository visibility with the user; default to private when unspecified.

## Deletion and correction

If a source is withdrawn:

1. Remove it from raw/approved storage.
2. Mark or remove its manifest record.
3. Remove its evidence from candidate and approved rules.
4. Re-run regression; demote any rule that no longer meets its evidence and approval basis.
5. Create a new snapshot. Do not overwrite historical snapshots silently; record the withdrawal reason.
