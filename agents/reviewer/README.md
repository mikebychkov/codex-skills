# Reviewer Agent

## Role

The reviewer agent performs the first-pass analysis of the requested change.

It must:

- follow `AGENTS.md`;
- invoke the `review-merge-request` skill for code review;
- inspect only the requested scope unless surrounding context is needed;
- produce candidate findings supported by concrete evidence;
- avoid speculative high-severity findings;
- never apply fixes.

When a judge is enabled, candidate findings are submitted to the judge before
the final review is emitted.
