# Executable Python hooks — lifecycle contract

Python 3.9+ standard library; Git must be installed. Harness invokes:

1. `init-review/hook.py` exactly once, **at review start**, independent of Maven.
2. Static analysis, regardless of Maven availability.
3. `before-validation/hook.py` to check integrity and `MAVEN_SETTINGS`.
4. Optionally execute permitted Maven validation.
5. **Always** execute `after-validation/hook.py`, including after failed tests.
6. **Always** execute `verify-working-tree/hook.py`, even if validation is skipped.

`environment/example-validation-run.py` illustrates invocation and nonzero-exit handling; it is not a sandbox or full harness. The caller must perform static review separately.

## Environment

- `TARGET_REPO`: required, absolute Git worktree root.
- `REVIEW_STATE_DIR`: required, absolute, **new, unique and nonexistent** directory for `init-review`. The harness owns its lifecycle and must not reuse it. Keep it outside the target repository, the per-worktree Git directory and the common Git directory; paths through existing symlinks are resolved before writes.
- `MAVEN_SETTINGS`: required only for Maven validation; checked by `before-validation` without displaying its contents.
- `REVIEW_SYSTEM`: required by example runner only.

Baseline is written once as `baseline.json` (exclusive creation, permissions 0700 on state directory). No automatic removal, restore, or cleanup of repository content.

## Exit status

- `0`: success
- `2`: missing required argument
- `3`: Maven settings unavailable (skip Maven, continue review)
- `4`: invalid repository
- `10`: integrity violation (stop mutation-capable validation)
- `11`: baseline unavailable or unreadable
- `12`: unsafe/shared/reused state directory

Only hashes of state are stored. Checks cover tracked status/diffs, staged entries, `HEAD`, symbolic branch, refs including tags, and shared/per-worktree Git config (`config` and `config.worktree`). This detects differences *between snapshots*, not transient changes that are undone between checks. Untracked/ignored files, reflogs, global Git config and filesystem permission/mode changes not represented in Git are not fully guaranteed. True filesystem/network security requires external sandbox/mount policy.
