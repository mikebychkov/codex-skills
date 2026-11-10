# Review Output Contract

Use this structure:

    Review verdict

    Findings

    Pre-existing observations

    Commands executed

    Validation results

    Validation limitations

    Rule Coverage Report

    Working-tree status

Order findings from highest to lowest priority.

If there are no findings, state:

    No actionable defects were found in the reviewed changes.

For every finding include:

- stable finding ID (for example F001);
- priority: P0, P1, P2, or P3;
- exact file;
- minimal relevant line range;
- concise title;
- concrete defect description;
- runtime, compilation, security, or maintenance impact;
- evidence supporting the finding;
- recommended correction;
- validation method.

`Commands executed` must come from the actual harness/tool command log when
available. Do not reconstruct commands from memory if an authoritative log is
available.

Under `Validation limitations`, mention checks that could not be performed.

Under `Working-tree status`, report whether tracked working-tree state changed
relative to the review start.

The final line must be:

    No project files were intentionally modified during this review.

This final line is a statement of reviewer intent. It must not replace the
objective working-tree verification result.


## Rule Coverage Report

Report totals for registered, applicable (including possibly applicable
UNVERIFIED), passed, failed, not applicable and unverified rules. State the
validator result: `VALID_COMPLETE`, `VALID_INCOMPLETE`, `INVALID`, or explicitly
`NOT_RUN` when validation was unavailable. INVALID/NOT_RUN are never complete.

List **every** registered rule, not only rules producing findings:

| Rule ID | Status | Evidence / Reason |
|---|---|---|
| actual registered ID | PASS / FAIL / NOT_APPLICABLE / UNVERIFIED | Inspected file/range, verification and evidence; finding IDs for FAIL; applicability reason or limitation and needed checks otherwise |

Report manifest identity and distinguish registered files, files supplied,
confirmed reads (only with actual event evidence), reviewer-declared evaluations,
validator results and judge assessments (only when executed). State missing
observability or judge integration explicitly. Validation establishes structure
and internal consistency, not semantic correctness or detection completeness.

Link `rule-coverage.json`, `ruleset.json`, `rule-coverage-validation.json` and
`rule-coverage-audit.jsonl` separately when artifact storage is available. Store
artifacts only under the external review state/output directory, never the
reviewed source repository. Preserve every existing output section and the final
integrity statement above as the last line of the emitted review.
