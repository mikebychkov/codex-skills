---
name: review-merge-request
description: Review a requested merge request, pull request, branch diff, commit, staged change, or uncommitted change in a source-read-only manner using high-confidence engineering rules.
---

# Merge Request Review

## Goal

Find actionable defects introduced or exposed by the requested change without
modifying tracked repository content or Git state.

Prefer a small number of high-confidence findings over a large number of
speculative observations.

## Inputs

The review target may be:

- uncommitted changes;
- staged changes;
- a commit;
- a branch diff;
- a merge request or pull request diff.

The caller or harness is responsible for identifying the requested target.

## Review procedure

1. Determine the exact requested change set.
2. Inspect the diff before examining surrounding code.
3. Inspect surrounding code only when needed to understand the changed behavior.
4. Identify the affected technologies and load only applicable references and
   rules.
5. Review in this priority order:
   - compilation and API correctness;
   - logical and functional correctness;
   - runtime exceptions and null handling;
   - regressions and backward compatibility;
   - Spring configuration and dependency injection;
   - transaction boundaries;
   - concurrency and thread safety;
   - authentication and authorization;
   - validation and error handling;
   - database consistency and Flyway migrations;
   - inefficient database access and resource leaks;
   - changed-behavior test coverage;
   - Maven/build configuration;
   - CI/CD behavior when CI/CD files are in scope;
   - maintainability.
6. Run validation only when permitted by harness policy and the Maven environment
   contract.
7. Separate source defects from environment limitations.
8. Send candidate findings to the judge when the configured workflow includes a
   judge.
9. Produce output using `assets/output-format.md`.

## Finding threshold

Report a finding only when all of the following are true:

- the issue is visible in the change or is a direct consequence of it;
- there is a plausible concrete failure or maintenance scenario;
- the evidence can be tied to a specific file and minimal relevant line range;
- the claim is not based only on an unavailable external dependency or service.

Do not produce large numbers of speculative findings.

## Scope discipline

Use `references/scope.md`.

In particular:

- do not present unrelated pre-existing issues as introduced by the patch;
- unfinished or placeholder code is a finding only under the conditions defined
  in the scope reference;
- environment limitations must not be converted into source-code defects.

## Maven validation

Use `references/maven-validation.md`.

Never run Maven without the external settings argument.

Prefer Maven Wrapper when present.

Permitted validation commands are limited to:

    ./mvnw -s "$MAVEN_SETTINGS" compile
    ./mvnw -s "$MAVEN_SETTINGS" test
    ./mvnw -s "$MAVEN_SETTINGS" verify

or, when no wrapper exists:

    mvn -s "$MAVEN_SETTINGS" compile
    mvn -s "$MAVEN_SETTINGS" test
    mvn -s "$MAVEN_SETTINGS" verify

Do not run deploy, release, version-update, formatter, repair, or dependency
purge commands.

## Docker

Do not use Docker for ordinary source validation.

Review Dockerfile or GitLab CI/CD only when the requested scope warrants it.

Do not run Docker commands unless explicitly authorized for the current review.

## Validation failure handling

When compilation or tests fail:

1. preserve the exact command from the harness command log;
2. summarize the relevant error;
3. determine whether the failure was introduced by the reviewed change;
4. distinguish source-code defects from environment limitations;
5. continue static analysis when possible;
6. do not modify files to make the build pass.

Unavailable Maven settings, Nexus, network, databases, Redis, Kafka, Docker,
credentials, certificates, or provider services are validation limitations
unless the reviewed change specifically broke their configuration.

## References

Load as applicable:

- `references/scope.md`
- `references/java.md`
- `references/spring.md`
- `references/database.md`
- `references/security.md`
- `references/testing.md`
- `references/severity.md`
- `references/maven-validation.md`

Concrete reusable rules live under:

- `rules/generic.md`
- `rules/team-review-rules.md`

Apply applicable rules only to changed code and honor the explicit
exceptions and false-positive guards in each rule.

## Final verification

Before finalizing:

- remove duplicate findings;
- remove speculative findings;
- confirm each finding is attributable to the reviewed change or clearly marked
  as pre-existing;
- confirm file and line evidence is minimal and accurate;
- verify severity against `references/severity.md`;
- preserve environment limitations separately from findings;
- include harness-provided command history and working-tree verification when
  available.

The final review must not claim that files were unchanged unless the
working-tree verification supports that claim.

## Hook lifecycle

Initialize baseline at review start with `hooks/init-review/hook.py`, independent
of Maven availability. Before each validation, call `before-validation`; after
each attempted validation, always call `after-validation` (including nonzero
exit status). Run final `verify-working-tree` even if Maven is skipped.
Use unique external `REVIEW_STATE_DIR` per review. Preserve Maven exit status.
