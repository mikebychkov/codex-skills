# Testing Review Reference

Check whether changed behavior has appropriate test coverage.

A missing test is actionable when the patch introduces meaningful behavior or a
regression-sensitive path that is not otherwise validated.

Do not demand tests solely for unchanged legacy behavior.

When tests cannot run because of environment limitations, keep that limitation
separate from source-code findings.
