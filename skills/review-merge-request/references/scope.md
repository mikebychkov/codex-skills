# Review Scope and Evidence Rules

## Requested change only

Review only the change set requested by the caller.

Do not report unrelated pre-existing issues as defects introduced by the patch.

Classify observations as one of:

1. introduced or exposed by the reviewed change;
2. pre-existing observation;
3. environment or validation limitation;
4. non-blocking observation.

## Existing unfinished code

Methods returning `null`, empty responses, placeholder values, or throwing
`UnsupportedOperationException` are actionable findings only when at least one
of the following is true:

- the reviewed change introduced the behavior;
- the reviewed change modified the method;
- the reviewed change exposes the method through a production API;
- the behavior contradicts an explicit contract;
- callers clearly depend on completed behavior;
- the behavior causes a concrete compilation or runtime defect.

If unfinished code is pre-existing and unrelated to the reviewed changes, place
it under `Pre-existing observations` rather than presenting it as a patch
defect.

## Evidence quality

Prefer findings supported by a concrete execution path.

Avoid theoretical warnings when no plausible runtime, compilation, security, or
maintenance impact can be demonstrated.

Do not infer a source defect solely from an unavailable service or missing
review-environment dependency.
