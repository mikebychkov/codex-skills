# Consistency Check

## Result

The decomposed review system preserves the original intent and does not
introduce a review model that contradicts the original `AGENTS.md`.

## Checked invariants

- Source and tracked Git state remain read-only.
- The reviewer never applies fixes.
- Maven is never allowed without the explicit external settings argument.
- Missing Maven settings remain an environment limitation.
- Docker is not a fallback for failed Maven validation.
- External systems and network access remain denied by default.
- Secrets remain non-displayable.
- Pre-existing defects remain separate from patch defects.
- High-confidence, non-speculative findings remain preferred.
- P0/P1 still require concrete evidence.
- Validation failures do not stop static analysis when it can continue.
- Unexpected tracked modifications are reported and are not auto-repaired.
- Review output preserves the original required sections and final disclaimer.

## Resolved ambiguity from the original

The original file said both:

- "Do not modify the project under any circumstances", and
- Maven validation may create `target/` build output.

The new structure resolves this by defining the invariant as:

> tracked source content and Git state are read-only; ignored build output from
> explicitly permitted validation is acceptable.

This is a clarification of the original operational intent, not a relaxation of
its source-code safety requirement.

## Minimal new mechanism

The new reviewer/judge split is intentionally minimal:

- the reviewer proposes evidence-backed findings;
- the judge validates attribution, evidence, severity, duplication, and
  environment-vs-source classification;
- neither agent can modify the target repository.

The judge therefore strengthens the original preference for high-confidence
findings rather than changing review semantics.
