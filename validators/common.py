"""Strict JSON input and external artifact storage using existing hook guards."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError(f"Invalid JSON constant: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=pairs, parse_constant=invalid_constant)


def external_state():
    # Existing guard resolves symlinks and excludes source, worktree Git and common Git.
    sys.path.insert(0, str(ROOT / "hooks"))
    from _integrity import paths, baseline, HookError
    try:
        repo, state = paths()
        if baseline(state).get("repository") != str(repo):
            raise ValueError("Review baseline belongs to another repository")
        return repo, state
    except HookError as exc:
        raise ValueError(str(exc)) from exc


def write_artifact(name, data):
    if not isinstance(name, str) or Path(name).name != name or name in ("", ".", ".."):
        raise ValueError("Artifact name must be a plain file name")
    _, state = external_state()
    destination = state / name
    # Exclusive creation: do not overwrite earlier reports or follow file symlinks.
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return destination
