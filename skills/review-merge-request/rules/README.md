# Review Rules

This directory contains concrete reusable review rules.

Each rule should define:

- a stable rule ID;
- applicability conditions;
- the violation condition;
- explicit exceptions where useful;
- default severity;
- rationale;
- optional good/bad examples.

Rules should minimize false positives and should not restate generic language
from references unless they add a concrete detection criterion.

- `team-review-rules.md`: team conventions extracted from annotated MR comments.
