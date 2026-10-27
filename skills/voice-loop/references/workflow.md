# Voice learning workflow

## Data entry

For every input, answer four questions before using it:

1. Who produced it?
2. Is the user allowed to use it for this profile?
3. Is it writing, spontaneous speech, a prepared spoken script, or an edited final?
4. Is it identity evidence or only a benchmark?

The answer to question 1 must be explicit. Do not infer identity from a folder name, topic, voice similarity, or prior sample. If the person is unlabeled, ask before ingestion. If the person differs from the active profile, stop and route to that person's isolated profile; when none exists and the user wants an ongoing loop, create a new person-specific profile and skill rather than using a temporary shared bucket.

Recommended starting set:

- 8–15 approved samples across the intended use cases.
- 5–10 AI-draft → human-final correction pairs.
- One fact card and one list of forbidden assumptions.
- At least three regression briefs.

Volume is not a substitute for coverage. Ten near-duplicate posts from one day may contain less evidence than five pieces across distinct contexts.

## Normalize without flattening

Clean transport noise, not voice:

- Remove timestamps, subtitle indices, encoding artifacts, duplicated caption fragments, and obvious transcription placeholders.
- Preserve hesitations, fragments, self-corrections, slang, punctuation choices, and paragraph rhythm when they are genuinely part of the voice.
- Keep raw and cleaned files separate.
- Never silently “improve” a sample before using it as identity evidence.

## Extract observable signals

Useful signals are concrete and testable:

- Opening move: judgment, scene, question, contradiction, anecdote.
- Sentence rhythm: median clause length, alternation of short/long units, punctuation.
- Structure: conclusion first, delayed thesis, list, story-to-principle.
- Evidence: personal scene, number, analogy, cited source, counterexample.
- Stance: certainty markers, hedges, direct address, distance from audience.
- Transitions: recurring connectors and where they occur.
- Spoken delivery: breath groups, fillers, restart behavior, stress words.
- Avoidances: phrases, abstractions, summaries, rhetorical templates the person repeatedly removes.

Bad rules:

- “He is warm and wise.” — personality guess, not executable.
- “Always use three sections.” — overgeneralized from format.
- “Write about AI.” — topic, not voice.

Better rules:

- “In Douyin spoken openings, state the disputed judgment in the first two clauses; do not begin with a generic greeting.”
- “When introducing a concept, follow it with one concrete work scene before giving a definition.”

## Rule lifecycle

```text
observation → candidate → human confirmation → regression → approved
                                      ↘ conflict/decline → candidate or retired
```

- A candidate may accumulate evidence from corrections.
- Three pieces of evidence count as independent only when their `source` fields differ.
- Human confirmation is mandatory even when the evidence threshold is met.
- Explicit human approval may override the threshold, but the approval must say it is low-evidence.
- Conflicting candidates should usually be split by mode, channel, format, or period.

## Generation loop

1. Freeze the task brief: audience, goal, channel, length, mode, facts, call to action.
2. Retrieve only applicable approved rules and 3–5 close examples.
3. Build a factual outline.
4. Draft for task completion.
5. Apply voice constraints.
6. Run factual, de-AI, and mode-specific checks.
7. Deliver a clean version.
8. If the user edits it, record the pair and repeat the learning loop.

Do not aim for maximum imitation density. Overloading every sentence with signature phrases makes the output less human and overfits the profile.

## Correction analysis

Compare draft and final at three levels:

- **Meaning:** What claims, examples, or position changed?
- **Structure:** What moved, disappeared, or became the lead?
- **Surface:** Which words, transitions, sentence lengths, or spoken rhythms changed?

Then classify:

- Fact corrections update `facts.md`.
- Content changes stay with the task unless repeated across sources.
- Format changes become channel/format constraints, not global identity rules.
- Style changes may become candidates.
- Mixed changes must be split into separate notes.

## Maintenance

- Review candidate rules after every 5–10 corrections.
- Retire rules that no longer match recent approved material.
- Keep period-specific rules scoped rather than rewriting history.
- Snapshot only after audit and regression.
- Never publish the profile corpus as part of a generic skill release.
