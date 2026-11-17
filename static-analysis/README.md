# Offline Java style analysis

`run_checkstyle.py` supplies evidence for the existing Rule Coverage Report;
it is not another reviewer or coverage system. Python standard library, local
Git, Java 21+ and the pinned standalone distribution are required. It does not
invoke Maven, Docker, target scripts, fixes or network clients.

## Installation and updates (setup only)

Pinned distribution: **Checkstyle 14.4.0**, `checkstyle-14.4.0-all.jar`.
The all-in-one dependency is installed at `checkstyle/jar/checkstyle.jar`.
Its locally computed SHA-256 is recorded in `distribution.json`:
`c0a521e54eabd1ece4ff7bd84cf231b012615745ed3aa4fb27ab0ca73097250c`.
This records the installed bytes; it is not an independent publisher-provenance
verification. The Maven artifact without bundled dependencies is unsuitable.

A maintainer must obtain the all-in-one release asset from the URL recorded in
`checkstyle/distribution.json` using an authorized setup process, not an MR
review. Verify its provenance and SHA-256 against a trusted independent release
record before installation. Place the verified file at
`static-analysis/checkstyle/jar/checkstyle.jar`, and record the actual 64-character
lowercase SHA-256 in `checkstyle/distribution.json`. Do not use CHECKSTYLE_JAR or
search target repositories/home for installations. No installer or review command
downloads or replaces the binary. SHA-256 proves integrity relative to the
reviewed pin, not publisher authenticity.

For example, after obtaining a trusted asset outside the target repository:

```sh
shasum -a 256 /approved/setup/checkstyle-14.4.0-all.jar
# After comparing with the trusted checksum:
mkdir -p static-analysis/checkstyle/jar
cp /approved/setup/checkstyle-14.4.0-all.jar static-analysis/checkstyle/jar/checkstyle.jar
# Record that checksum in checkstyle/distribution.json before verification.
python3 -B -c 'import importlib.util; from pathlib import Path; p=Path("static-analysis/run_checkstyle.py").resolve(); s=importlib.util.spec_from_file_location("sa", p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.verify_distribution())'
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

The verifier checks readability, the recorded hash, ZIP integrity, the executable
manifest, required check/dependency classes and the actual `java -jar --version`
response. Running the real suite also verifies that the bundled configuration,
including XPath coverage guards, executes. A checksum/version match alone is
not a behavior test. If syntax/configuration/runtime support fails, no PASS is
issued. The known Checkstyle configuration DTD is resolved by Checkstyle from
its bundled resources; no target-provided configuration or external DTD is used.
Enforce network denial in the execution harness as well as this no-download code.

To update, review a specific new release and its behavior, replace the binary
and version/hash together **during setup**, run all real integration tests,
and review changed diagnostics/limitations before committing the new pin. Normal
reviews must never perform updates. Preserve Checkstyle's license with any
redistributed binary; see the upstream release's license/distribution materials.

## Review command and storage

Initialize the existing integrity baseline and registry first, as documented in
`../validators/README.md`. Set TARGET_REPO and an external REVIEW_STATE_DIR.
From any working directory (use an absolute adapter path):

```sh
python3 /absolute/review-system/static-analysis/run_checkstyle.py --source HEAD --target staging --review-id review-unique-id
```

The comparison resolves local commit IDs and `target...source` merge base.
Git diff provides added-line ranges; a single ls-tree/cat-file batch reads the
changed files without per-file Git subprocesses. Complete source blobs come from the
resolved source commit, including files whose working copy differs. No checkout,
index update or Git write occurs. Lazy fetching is disabled and Git transports
are denied, including in partial clones with missing local objects. One analysis JVM handles all changed Java
files; a small separate `--version` JVM verifies the executable distribution.
Artifacts, UTF-8 snapshots and JVM working directory are outside the target in
guarded review state. The snapshots are removed after execution. Deleted files,
rename-only changes and deletion-only Java hunks have no introduced lines.
Edited renames use destination coordinates. Symlinks/binary Java and inaccessible
refs produce explicit limitations. Non-branch scopes are not implemented: retain
UNVERIFIED for these rules rather than silently reviewing the wrong scope.

`static-analysis-results.json` records resolved scope, repository, version/hash,
file ranges, diagnostics with line/column/status, existing-format findings and
evaluations, limitations and elapsed wall time (including Git/export/verification).
Raw stderr, source snippets and arbitrary analyzer messages are not emitted.
Known checks receive safe normalized messages, so credentials in source/output
are not copied into reports. Stable finding IDs use the rule and location hash.
Audit uses the existing external JSONL logger with real `static_analysis_started`
and `static_analysis_result` events; these are not model-read or judge receipts.
The adapter checks the existing integrity snapshot before/after even on failure,
independently of Maven settings. A changed tracked/Git state stops artifact
publication; nothing is automatically restored.

Use `findings` and `evaluations` directly in the normal coverage assembly. Or
pass `--coverage-draft /external/draft.json` to create a separate
`rule-coverage-static-draft.json`, structurally validated with the existing
validator. Target identity must equal the result's absolute repository and
resolved `merge-base..source-commit`, and review IDs must match. Unrelated rules
are retained; finding ID collisions fail rather than overwrite. After judge or
manual revisions, run the normal final coverage validator and Markdown renderer.
There is no additional coverage schema. Do not duplicate deterministic findings
in the reviewer pass. Report output links and performance timing normally.

## Coverage and attribution

- PASS: all relevant submitted files were accounted for, the JVM/XML identity
  and exit status are consistent, and no rule-specific gaps or introduced
  violations occurred within the supported check domain.
- FAIL: confirmed violations overlap added lines and have concrete finding IDs.
- NOT_APPLICABLE: no relevant added/modified Java lines. Generated paths are
  excluded for FQCN only; static-import convention retains its existing scope.
- UNVERIFIED: execution/dependency/parser/file coverage failure, known FQCN gap,
  or uncertain unchanged-line FQCN attribution. Incomplete takes precedence over
  FAIL for coverage because the existing UNVERIFIED schema disallows finding
  references; independently confirmed findings remain in Findings. A globally
  invalid execution/XML result cannot supply actionable findings.

Static imports on unchanged lines are classified OUTSIDE_CHANGED_LINES and
excluded. Unchanged-line FQCN diagnostics might reflect legacy code or a removed
naming conflict; they are separately classified and require targeted attribution,
never silently promoted into findings. A diagnostic column is the Checkstyle AST
location, not necessarily the first character of a complete qualified name.
Changed-line intersection is deliberately conservative; do not invent locations
when a multi-line expression or indirectly changed context prevents attribution.

## Pinned check limitations

Behavior was inspected in the upstream [14.4.0 source](https://github.com/checkstyle/checkstyle/blob/checkstyle-14.4.0/src/main/java/com/puppycrawl/tools/checkstyle/checks/imports/UnnecessaryFullyQualifiedTypeCheck.java).
The check handles declarations/return types and `new` type references and tracks
some naming conflicts. It is not a Java compiler or complete symbol resolver.
Qualified annotations and nested-type references are omitted; package naming
conventions influence recognition, and third-party wildcard conflicts cannot be
resolved without dependencies. See the [official check documentation](https://checkstyle.org/checks/imports/unnecessaryfullyqualifiedtype.html).
The installed distribution and configuration passed all 76 automated tests on
2026-11-17, including real Checkstyle behavior and execution from another cwd.
Mocked adapter tests alone cannot establish the check's behavior; installations
without a binary must still report real integration tests as skipped.

A bundled MatchXpath guard conservatively signals annotations (including Generated),
class literals, nested-type forms, type parameters, wildcard imports and chained
qualified expression forms that the core check cannot cover reliably. A signal
makes FQCN coverage UNVERIFIED for that file and leaves its FQCN diagnostics as
REQUIRES_VERIFICATION, without speculative findings. This may over-classify safe
code: targeted inspection during normal review can resolve those contexts.
Package/import declarations, comments/Javadoc and strings are not executable
AST type references. Generated directories named `generated`,
`generated-sources` or `generated-test-sources` are excluded from FQCN. Other
generated locations must be identified during normal diff classification and
passed as repeatable `--generated-path relative/file/or/directory` options; these
are recorded in the file metadata and excluded from FQCN deterministically; do not accept diagnostics from
known generated source. Unconventional uppercase package segments and compiler-
level naming conflicts need targeted evidence; a clean syntax check is not proof
of all Java name resolution or all repository-specific generated-code boundaries.

## Tests and performance

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Adapter tests use temporary local Git repositories and synthetic XML, explicitly
separate from `RealCheckstyleTests`. Real tests use only the bundled JAR and skip
with an explicit reason if it is absent; an installed but invalid JAR causes
failures, not skips. The real suite covers the requested type-reference forms,
ignored text/import/package contexts, naming conflicts, parser failure, static
imports and execution from a different cwd. Adapter tests cover diffs, renames,
deletions, partial output, statuses, coverage validation, batching and unchanged
source/Git state. Runtime output `elapsed_seconds` measures the actual added
cost. Without a JAR no real analysis timing or syntax-detection success is
claimed; test timings for mocked XML are not a JVM benchmark.

## Naming collisions are a separate review criterion

JAVA-NAMING-001 requires a P3 finding when a demonstrated collision between
same-simple-name types forces a qualified reference in changed code. The core
UnnecessaryFullyQualifiedType check intentionally accepts such qualification;
its silence does not establish PASS for the naming rule. The reviewer evaluates
this additional criterion in the normal change-oriented inspection, using the
competing import/type identities and changed usage as evidence. No extra full
scan is required. The adapter continues to supply only JAVA-STYLE-001/002;
JAVA-NAMING-001 must receive its own evidence-based coverage declaration.
