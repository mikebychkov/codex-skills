# Rule Coverage Reporting

This supplements the MR review skill; it does not replace source review, judge
assessment, security policy enforcement, or the existing integrity lifecycle.
Python 3.9+ standard library and Git are sufficient. No services or packages are
downloaded. The registry and validator default to printing JSON on stdout.

## Commands and artifact placement

From the review-system directory, with `TARGET_REPO` set to the absolute target
worktree root, choose a new unique absolute external `REVIEW_STATE_DIR`. Keep the
existing hook lifecycle unchanged:

```sh
export TARGET_REPO=/absolute/path/to/review-target
export REVIEW_STATE_DIR=/tmp/review-unique-id
export PYTHONDONTWRITEBYTECODE=1
python3 hooks/init-review/hook.py
python3 validators/rule_registry.py --review-id review-unique-id --write-artifacts --supply
```

The final command creates `ruleset.json`, registers the rules and outputs the
rule-file contents to the review process. Supplying bytes is not confirmation
that the model read them. The reviewer must actually consider every registered
ID, load applicable definitions, and prepare a report matching
`skills/review-merge-request/assets/rule-coverage.schema.json`. Use a temporary
input such as `$REVIEW_STATE_DIR/rule-coverage-draft.json`, never a target source
file. The target `change` must identify the exact review scope (prefer resolved
source/target commits and merge base for branch reviews). `repository` must be
the absolute target root, `review_id` must match the registry invocation.

After source review and any real judge assessment:

```sh
python3 validators/validate_coverage.py "$REVIEW_STATE_DIR/rule-coverage-draft.json" --write-artifacts
python3 hooks/verify-working-tree/hook.py
```

The validator creates `rule-coverage.json`, `rule-coverage-validation.json`, and
`rule-coverage.md`, and appends reviewer declarations and its result to
`rule-coverage-audit.jsonl`. Artifact creation is exclusive: existing reports are
never overwritten. Use a new external state for a new run; retain earlier
artifacts. JSON parsing rejects duplicate keys and nonstandard numeric values.
Audit events carry UTC timestamp, review ID, source, event type and rule IDs.
Schema-invalid reports are retained as invalid inputs and their validator result
is logged without importing reviewer evaluations. Parse/configuration failures
are logged when an initialized audit identity is available; otherwise stdout
explicitly reports that audit logging was unavailable.
Only include safe source evidence; never credentials or external settings values.

`--write-artifacts` uses the existing hook path guards and checks the baseline's
repository binding. It rejects storage inside source or Git directories,
including linked worktree/common Git paths and symlink aliases. The validator
also checks the report repository against the baseline and review ID against
`coverage-identity.json` created by the registry audit operation. Read-only invocations
without this option print diagnostics and create no review artifacts. A Python
process may generate bytecode unless `PYTHONDONTWRITEBYTECODE=1` is set; the
commands above disable it.

Before and after each permitted Maven validation, continue invoking the existing
`before-validation` and `after-validation` hooks. Always run final
`verify-working-tree`, even if coverage is invalid/incomplete or Maven cannot
run. Maven still requires `-s "$MAVEN_SETTINGS"`; this tooling neither inspects
nor changes settings and does not authorize network, Docker or target writes.

## Registry

```sh
python3 validators/rule_registry.py
python3 validators/rule_registry.py --rules-dir /absolute/configured/rules
```

The explicit directory contains `rule-files.json` listing immediate Markdown
files. README is metadata; no recursive discovery occurs. Missing, unconfigured,
symlinked, malformed or duplicate definitions fail. Each rule uses the existing
`## ID — Title` header and generic/team field conventions documented in the rules
README. Manifests contain file SHA-256, rule IDs, titles and declaration lines.
Files are sorted by name; rules retain source order. Manifest identity is SHA-256
of UTF-8 canonical JSON (`sort_keys=True`, compact separators,
`ensure_ascii=False`) over version and files, excluding the identity itself.
Timestamps and absolute installation paths are excluded, so output is stable.
All live rule definitions and hashes are compared with the embedded manifest;
a stale or modified ruleset is INVALID. The manifest's file entries enumerate
registered rules; evaluation entries carry only their IDs and declarations.

## Coverage semantics and schema

- PASS applies and has inspected locations, performed-check description and
  supporting evidence. Missing findings never imply PASS.
- FAIL has a concrete violation, line ranges, evidence and one or more finding
  IDs present in the report. A finding can support more than one applicable
  rule; multiple findings per rule are supported.
- NOT_APPLICABLE needs a contextual applicability reason.
- UNVERIFIED applies or may apply, and needs a limitation plus checks/evidence
  still needed. No automatic promotion to PASS.

Every evaluation has `reason`, `inspected`, `evidence`, `finding_ids`,
`limitations`, and `needed`; unused arrays are empty. `reason` describes the
check for PASS/FAIL or applicability/limitation otherwise. `inspected` uses
`file` and optional paired `start_line`/`end_line`; FAIL and finding locations
require ranges. Findings retain stable IDs and P0–P3 priority. Findings not tied
to a registered rule are permitted; do not stretch rules to fit them.

The summary counts registered, passed, failed, not_applicable, unverified and
applicable. Applicable conservatively equals PASS + FAIL + UNVERIFIED, including
rules whose applicability remains uncertain. Completion means structural
coverage, not clean code: a report with FAIL can be VALID_COMPLETE.

| Classification | Exit code | Meaning |
|---|---|---|
| VALID_COMPLETE | 0 | One structurally supported declaration per registered rule; no UNVERIFIED |
| VALID_INCOMPLETE | 3 | Structurally valid, with at least one UNVERIFIED |
| INVALID | 2 | Schema, registry, reference, hash, summary, I/O or configuration error |

The registry returns 0 on success and 2 for invalid configuration/input.
A CLI usage error also returns 2. Never silently repair a report. Whitespace-only
required strings and reversed ranges are invalid. The bundled schema is Draft
2020-12 and can also be consumed by standard JSON Schema libraries. To avoid a
runtime dependency, `schema_contract.py` implements **only** its used keywords,
rejecting unsupported keywords. It is not a general JSON Schema engine or
metaschema validator; adding schema vocabulary requires implementation and tests.

Structural validity cannot prove that files were inspected, evidence is true,
findings are genuine, a rule was semantically verified, or all violations were
detected. Those remain reviewer responsibilities and, when run, judge checks.

## Audit provenance and integration limits

- `rules_registered` / `registry`: actual registry operation, manifest hash.
- `rule_files_supplied` / `registry`: file bytes output to the process on stdout,
  with hashes. This is not a reviewer read receipt.
- `reviewer_evaluation` / `reviewer_declared`: evaluations imported from the
  report, not tool execution evidence. Rejected reports may contain declarations
  that do not survive validation; consult validator_result.
- `validator_result` / `validator`: actual structural validation outcome.
- `tool_read_confirmed` / `harness_observed`: reserved for an integrating harness
  that actually observed a read; requires its real event reference.
- `judge_result` / `judge_assessment`: only after an actual judge run; requires
  its execution reference and per-rule assessment/reasons in details.

`validators.audit.append_event(...)` is the integration API for observed-read
and judge events. It requires `event_reference` for these events and rejects
wrong source/type combinations. Trusted callers must supply genuine event
references and safe details; an arbitrary string cannot authenticate execution.
The local JSONL log is not tamper-proof. A state identity prevents accidentally
mixing reviews. Symlinked audit destinations are rejected.

There is currently **no tool-call interception and no judge runner**. Neither the
registry nor validator invents read-confirmed or judge events. The existing
`environment/example-validation-run.py` only illustrates Maven/integrity, not
reviewer or judge execution. Integrators must call these coverage commands as
part of their review workflow; the skill now requires them, but this does not
install enforcement in an external host. Read-only stdout mode needs a host to
retain stdout as an artifact/event. Unavailable artifact or tool observability
must be disclosed, not represented as successful execution.

## Reproducible example and tests

After initializing external state and registering/supplying rules as above:

```sh
python3 validators/example_coverage.py --review-id review-unique-id --change example-only
python3 validators/validate_coverage.py "$REVIEW_STATE_DIR/rule-coverage-draft.json" --write-artifacts
```

The example deliberately marks all rules UNVERIFIED: no semantic target review
was performed. Exit 3 is expected. It is an example, not evidence about a Java
repository. Use a separate external state from a real review.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Tests use temporary synthetic Git repositories, never existing review targets,
production systems, Docker or network. They exercise the registry, schema,
validator, CLI/audit/rendering flow, external path guards, existing hook lifecycle,
unavailable Maven settings and mutation detection. Existing audit JSON files are
historical results, not executable test suites. Existing hook and Maven runner
code is unchanged.

## Deterministic Java evidence

`../static-analysis/run_checkstyle.py` writes `static-analysis-results.json` in
this same guarded state. Its `findings` and `evaluations` use the existing
coverage schema; merge them during report assembly or use its validated optional
`--coverage-draft` bridge, then run the normal final validator/renderer.
It supplies JAVA-STYLE-001 and JAVA-STYLE-002 without a second LLM inspection
pass. Incomplete execution is UNVERIFIED, never an inferred PASS. See
`../static-analysis/README.md` for local merge-base scope, installation, known
coverage gaps, audit events and explicit real-test skips when the JAR is absent.
The audit event types `static_analysis_started` and `static_analysis_result`
have source `static_analyzer`; they do not attest model reads or judge execution.
