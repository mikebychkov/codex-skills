# Original AGENTS.md → New Structure Mapping

This document verifies that the important responsibilities of the original
monolithic `AGENTS.md` remain represented after decomposition.

| Original responsibility | New location |
|---|---|
| Purpose: code review/static analysis only | `AGENTS.md` |
| Read-only reviewer requirement | `AGENTS.md`, `policies/command-policy.yaml` |
| No edits/creates/deletes/renames/patches/commits/index changes | `AGENTS.md`, `policies/command-policy.yaml` |
| Build output exception under `target/` | `AGENTS.md`, `references/maven-validation.md`, working-tree hooks |
| Review only requested changes | `AGENTS.md`, `references/scope.md`, `SKILL.md` |
| Distinguish introduced/pre-existing/environment/non-blocking | `AGENTS.md`, `references/scope.md`, output contract |
| Review priority checklist | `review-merge-request/SKILL.md` + technology references |
| Java/Spring/Maven/Postgres/Flyway/Docker/GitLab project context | `AGENTS.md` |
| External Maven settings via `MAVEN_SETTINGS` | `AGENTS.md`, `references/maven-validation.md`, environment contract |
| Never use or create `./settings.xml` | `AGENTS.md`, Maven reference, secrets policy |
| Allowed Maven commands only with `-s "$MAVEN_SETTINGS"` | Maven reference, command policy |
| Missing Maven settings = environment limitation | `AGENTS.md`, Maven reference |
| Before/after `git status --short` around Maven | validation hooks |
| Do not auto-revert unexpected modifications | `AGENTS.md`, after-validation hook |
| Dockerfile is CI-oriented, not Maven fallback | `AGENTS.md`, network policy, skill |
| Allowed inspection commands | `policies/command-policy.yaml` |
| Forbidden state-changing shell/Git commands | `policies/command-policy.yaml` |
| No formatter/auto-repair actions | command policy, Maven reference |
| No external systems/network by default | `AGENTS.md`, `policies/network-policy.yaml` |
| No deploy/publish/upload/release | `AGENTS.md`, network policy, command policy |
| Do not expose credentials/secrets | `AGENTS.md`, `policies/secrets-policy.yaml` |
| Compilation/test failure procedure | `review-merge-request/SKILL.md` |
| Do not blame unavailable external dependencies | `SKILL.md`, Maven reference |
| Existing unfinished code handling | `references/scope.md` |
| P0-P3 priorities | `references/severity.md` |
| Finding fields | `assets/output-format.md` |
| Final review sections | `assets/output-format.md` |
| List every executed command | output contract + authoritative harness command log |
| Report validation limitations | output contract |
| Working-tree status | output contract + verification hook |
| Final "No project files..." line | output contract |

## Intentional improvements

The decomposition makes several constraints stronger without changing their
meaning:

1. Command and network restrictions move from prompt-only guidance into harness
   policy, where they can be technically enforced.
2. Working-tree checks move into hooks, reducing reliance on model memory.
3. Command history is expected from the harness/tool log rather than being
   reconstructed by the model.
4. The phrase "read-only" is clarified as **source/tracked-state read-only** so
   permitted Maven output under ignored `target/` directories does not conflict
   with the top-level invariant.
5. Review methodology and output format move into the skill, leaving
   `AGENTS.md` focused on stable system invariants and environment facts.
