# Legacy Bash vs updated Python: executed regression comparison

The legacy scripts were extracted unchanged from `review-system-with-team-rules-v2.zip` (only the executable bit was set for the legacy example runner). Each scenario ran in separate temporary Git repositories, with isolated state and fake Maven wrapper for integration tests. No production repository was modified. Python hook code was also exercised with additional edge cases.

| Scenario | Legacy Bash | Python | Expected interpretation |
|---|---|---|---|
| Unchanged tracked tree | 0 / 0 | 0 / 0 | Equivalent |
| Tracked file edited | 10 / 10 | 10 / 10 | Equivalent |
| Maven settings missing at start | 3; no baseline | init 0; baseline exists | Intentional fix: static-only review can finish |
| State path inside target | 12 **after creating directory** | 12 **without creating directory** | Intentional security fix |
| Re-initialize same state | 0; baseline overwritten | 12; baseline retained | Intentional fix |
| Tag added after baseline | missed (0) | 10 | Integrity coverage fix |
| Switch branch at same HEAD | missed (0) | 10 | Integrity coverage fix |
| Local Git config changed | missed (0) | 10 | Integrity coverage fix |
| Missing baseline | 11 | 11 | Equivalent |
| Maven exits 7 and modifies tracked file | runner exits 7 without verification | runner exits 10 and verifies | Critical fix |
| Maven exits 7 without tracked changes | runner exits 7 | runner exits 7, integrity verified | Exit status preserved |
| Maven settings absent in runner | runner exits 3 | runner exits 0, skips Maven and verifies | Intentional: static analysis remains possible; unavailable Maven recorded |

## Additional Python-only edge cases

- Validation prerequisites fail but initial baseline remains valid and final verification still succeeds.
- Staged-file change detected (exit 10).
- Symlink resolving into source repo rejected before creation (exit 12).
- Independent review-state directories do not share baselines.
- Untracked-file exclusion behaves as documented.

## Remaining limits (deliberate)

- Snapshot comparison detects **state differences at check time**, not modifications undone between snapshots.
- Untracked/ignored files and reflogs are not included in the guarantee.
- YAML security/command policies are documentation until a real harness enforces them.
- This demo runner does not provide sandbox isolation; for strict read-only use a mounted read-only source and separate build workspace.
- The test runner uses a deliberately fake `mvnw` that exits with status 7 (and in one scenario changes a tracked file), not a real project Maven build.
