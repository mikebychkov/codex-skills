# Review Output Contract

Use this structure:

    Review verdict

    Findings

    Pre-existing observations

    Commands executed

    Validation results

    Validation limitations

    Working-tree status

Order findings from highest to lowest priority.

If there are no findings, state:

    No actionable defects were found in the reviewed changes.

For every finding include:

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
