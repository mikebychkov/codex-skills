# Linked worktree integrity fixes (v4)

## Findings corrected

1. Git configuration is now captured from the common Git directory (`config`) and from the worktree-specific Git directory (`config.worktree`), if present. This replaces the old incorrect `git_dir/config` assumption.
2. State directory containment checks now exclude the source working tree, the per-worktree Git directory and the common Git directory, before creating any filesystem objects. Existing symlinks are resolved before checking.

## Verification

`audit/linked-worktree-tests.json` records ten passing isolated Git tests covering normal and linked worktrees, both configuration variants, rejected state paths, symlinks, and changed tracked content.

## Remaining limits

- Snapshot checking does not prevent or detect transient changes that are reversed between snapshots.
- An untrusted concurrent process could race path verification; enforce filesystem restrictions and isolation in the harness.
- The snapshot deliberately does not claim to capture all Git metadata, reflogs, global config or ignored/untracked content.
