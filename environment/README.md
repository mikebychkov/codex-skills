# Review environment

The review system is separate from target repository; `AGENTS.md` and skills are supplied by the harness.

Required: `TARGET_REPO`, `REVIEW_SYSTEM`; for Maven validation `MAVEN_SETTINGS`.
Review state: `REVIEW_STATE_DIR` must be unique and outside the target repository, normally created by the runner with a random UUID-based name.

Use `python3 environment/example-validation-run.py` for a minimal execution example. Static analysis and tool permission enforcement are responsibilities of the integrating harness, not this demo runner.

No hook writes target source, cleans artifacts, or repairs Git state.


Rule coverage is a separate mandatory MR review stage. See
[`validators/README.md`](../validators/README.md) for registry supply, schema
validation, external artifacts and audit provenance. The Maven example runner
does not execute a reviewer, intercept tool reads, or invoke a judge; integrating
hosts must call the coverage tools explicitly alongside the unchanged integrity
lifecycle. Policies remain in force for all new tool invocations.
