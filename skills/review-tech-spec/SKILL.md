---
name: review-tech-spec
description: Review a technical specification or implementation task against reusable engineering rules and report concrete ambiguities, contradictions, missing requirements, and implementation risks.
---

# Technical Specification Review

This skill is intentionally minimal in the initial structure.

Use it to review technical specifications without modifying source repositories.

Recommended flow:

1. identify actors, systems, inputs, outputs, state changes, integrations, and
   persistence changes;
2. load applicable references;
3. apply reusable rules;
4. distinguish blockers, major issues, minor issues, and clarification
   questions;
5. avoid inventing requirements;
6. prefer concrete ambiguity or contradiction over speculative design advice.

Add project-independent rules under a future `rules/` directory if this skill
is expanded.
