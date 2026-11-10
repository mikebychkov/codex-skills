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


## Deterministic registry format

`rule-files.json` explicitly lists all immediate Markdown rule files. README is
metadata; nested directories are not scanned. Unconfigured/missing files are
errors. Rule headings use `## STABLE-ID-001 — Title`. Generic rules require
Applies when, Violation, Default severity and Do not report when fields; team
rules require Applies to, Check, Default priority and Exceptions fields, using
the existing bold labels. Empty fields, malformed headings, duplicate IDs and
invalid severity are rejected. `## Reviewer instructions` is the existing
non-rule footer. Preserve all rule IDs and exceptions when editing definitions.
