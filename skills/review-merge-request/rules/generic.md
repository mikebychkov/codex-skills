# Generic Review Rules

## GENERIC-001 — Changed behavior must preserve explicit contracts

**Applies when:** a reviewed change modifies a public API, internal interface,
serialization contract, persisted representation, or externally observable
behavior.

**Violation:** the change breaks an explicit existing contract without a
compatible migration, versioning strategy, or intentionally documented breaking
change.

**Default severity:** P1 or P2 depending on demonstrated impact.

**Rationale:** contract regressions can break callers even when the changed code
compiles locally.

**Do not report when:** the contract is intentionally versioned or the caller
explicitly requested a breaking change and all affected consumers are handled.


## GENERIC-002 — Do not swallow failures that affect correctness

**Applies when:** changed code catches or converts an error on a path that
affects correctness, persistence, security, or an externally visible result.

**Violation:** the error is ignored or converted into apparent success without
a defined recovery or fallback behavior.

**Default severity:** P2; raise to P1 only with concrete evidence of serious
production, security, or data-consistency impact.

**Rationale:** silent failure can make an operation appear successful while the
required work did not complete.

**Do not report when:** the error is intentionally best-effort and that behavior
is explicit in the surrounding contract.
