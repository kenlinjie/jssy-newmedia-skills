# Profile schema

## Directory contract

```text
<profile>/
├── .gitignore
├── profile.json
├── facts.md
├── rules.json
├── corrections.jsonl
├── corpus/
│   ├── manifest.jsonl
│   ├── raw/
│   ├── approved/
│   └── benchmark/
├── eval/
│   ├── cases.jsonl
│   └── results/
└── versions/
```

The profile is private working data. The generated `.gitignore` ignores the entire profile by default. Change that only after an explicit privacy review.

One profile represents one explicitly identified person. Do not place multiple people's identity evidence, corrections, facts, or rules in the same directory. When identity is unknown, keep the input outside all profiles until the user identifies the person.

## `profile.json`

Required top-level fields:

- `schema_version`: currently `1.0`.
- `profile_id`: stable machine identifier.
- `display_name`: human label; it need not be a legal name.
- `language`: primary locale such as `zh-CN`.
- `modes`: one or more of `writing`, `spoken`.
- `status`: `learning`, `active`, or `paused`.
- `purpose`: arrays for audiences, channels, goals, and non-goals.
- `data_policy`: authorization and repository defaults.
- `promotion_policy`: evidence threshold and human-approval gate.
- `created_at`, `updated_at`: UTC RFC 3339 timestamps.

Do not store passwords, access tokens, government identifiers, medical records, or unnecessary third-party private data in the profile.

## `facts.md`

Keep three explicit sections:

1. **Verified facts** — user-confirmed claims that may be used.
2. **Needs verification** — plausible claims that may not be stated as fact.
3. **Forbidden assumptions** — claims the model must not infer.

Facts are content constraints, not style evidence. A repeated phrase does not prove the underlying claim is true.

## `corpus/manifest.jsonl`

One JSON object per source file:

```json
{"sample_id":"sample-001","path":"corpus/approved/001.txt","kind":"self-spoken","mode":"spoken","source":"episode-001","authorized":true,"identity_evidence":true,"date":"2026-07-22","notes":""}
```

Allowed `kind` values:

- `self-writing`
- `self-spoken`
- `human-final`
- `correction`
- `benchmark`

Invariants:

- Identity evidence requires `authorized: true`.
- A benchmark must use `identity_evidence: false`.
- `path` is relative to the profile when possible.
- `source` identifies an independently produced document, episode, talk, or revision unit. Multiple edits to the same source are not independent evidence.

## `rules.json`

Each rule has:

```json
{
  "rule_id": "r_1234567890",
  "text": "口播开头直接进入判断，不使用泛化寒暄。",
  "mode": "spoken",
  "scope": "global",
  "status": "candidate",
  "evidence": [
    {
      "correction_id": "corr_...",
      "source": "episode-012",
      "note": "人工删除寒暄开头",
      "added_at": "2026-07-22T12:00:00Z"
    }
  ],
  "approval": null,
  "created_at": "2026-07-22T12:00:00Z",
  "updated_at": "2026-07-22T12:00:00Z"
}
```

Allowed values:

- `mode`: `writing`, `spoken`, `both`.
- `status`: `candidate`, `approved`, `retired`.
- `scope`: `global` or a narrow label such as `channel:douyin`, `format:newsletter`.

Approval object:

```json
{
  "approved_by": "human name",
  "approved_at": "2026-07-22T12:10:00Z",
  "note": "用户明确确认",
  "independent_evidence": 3,
  "low_evidence_override": false
}
```

An approved rule always requires a human approval record. Evidence count alone never auto-promotes a rule.

## `corrections.jsonl`

One record per AI draft → human final pair. It stores both texts, hashes, category, reason, mode, scope, and source. This is private identity data and must not be copied into the skill repository.

Categories:

- `style`: stable expression preference may exist.
- `fact`: factual correction; update facts, not voice.
- `content`: one-off argument or detail change.
- `format`: layout, length, field, or platform constraint.
- `mixed`: separate the components before proposing rules.

## `eval/cases.jsonl`

Each regression case should have a stable ID, mode, brief, required facts, forbidden claims, and the failure it protects against. Keep expected wording flexible; regression is about behavior, not reproducing one answer verbatim.

## Versions

`versions/<label>/` is an immutable snapshot created by `snapshot_profile.py`. It includes configuration and metadata, never corpus text. Use a new label rather than overwriting a snapshot.
