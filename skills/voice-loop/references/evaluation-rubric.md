# Evaluation and regression rubric

Semantic quality cannot be proven by a script. Use this rubric as a human-readable gate; use `audit_profile.py` only for structural checks.

## Hard failures

Any hard failure blocks approval or versioning:

- Invented, conflated, or unauthorized fact.
- Benchmark material treated as proof of the person's identity or history.
- Candidate rule silently applied as an approved rule.
- Writing rule applied to spoken output, or vice versa, without evidence.
- Output misses the requested task, audience, channel, or length.
- Private corpus or corrections included in a publishable repository.

## Score dimensions

Score each dimension 0–2.

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Fact fidelity | invented or contradicts facts | uncertainty handled inconsistently | all claims supported or clearly marked |
| Task completion | misses the brief | partially satisfies it | achieves goal, audience, channel, length |
| Voice evidence | generic or caricatured | some applicable signals | approved rules used naturally and selectively |
| Specificity | abstract filler dominates | mixed abstract/concrete | concrete scenes, claims, and transitions carry the piece |
| Naturalness | obvious template/AI cadence | occasional formulaic passages | varied, coherent, human editing rhythm |
| Mode fitness | unreadable or wrong mode | usable with edits | written prose reads well or spoken copy is easy to say |

Maximum: 12.

Recommended acceptance:

- No hard failure.
- Total score at least 10.
- Fact fidelity and task completion must each score 2.
- New version must not score lower than the previous snapshot on any protected regression case.

## Spoken-mode checks

- Can the sentence be said in one comfortable breath?
- Are stress words close to where a speaker would naturally emphasize them?
- Do punctuation and line breaks help, rather than fight, delivery?
- Were literary headings, nested clauses, and written-summary phrases removed when they do not sound spoken?
- Does the opening start the actual point quickly?

## Writing-mode checks

- Does each paragraph advance the argument or scene?
- Are sentence lengths varied for meaning rather than artificially randomized?
- Are abstractions grounded with a concrete example where needed?
- Are headings and lists serving navigation instead of revealing a template?
- Does the ending resolve this piece rather than append a generic “in conclusion” paragraph?

## Regression protocol

Keep at least three stable cases:

1. **Anchor:** the most common real task.
2. **Known failure:** a brief that previously triggered AI flavor or a bad habit.
3. **Transfer:** a different topic that tests whether the voice rule generalizes.

For each rule change:

1. Generate with the previous approved snapshot.
2. Generate with the candidate change, keeping brief and facts fixed.
3. Blind-compare where practical.
4. Score both versions and record hard failures.
5. Approve the version only if protected cases do not regress.

Do not use exact-word matching as the main measure. A useful voice profile reproduces decisions and tendencies, not a memorized passage.
