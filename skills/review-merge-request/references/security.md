# Security Review Reference

Check changed code for concrete:

- authentication regressions;
- authorization bypass;
- unsafe trust-boundary changes;
- credential or secret exposure;
- injection paths;
- insecure validation;
- unsafe handling of externally controlled input.

Do not expose secret values in findings.

Do not inflate speculative security concerns into P0/P1 findings without
concrete evidence and a plausible impact path.
