"""Deterministic registry for explicitly configured immediate Markdown rule files."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validators.common import ROOT, load_json

DEFAULT_RULES = ROOT / "skills/review-merge-request/rules"
RULE_ID = r"[A-Z]+(?:-[A-Z]+)*-[0-9]{3}"
HEADING = re.compile(r"^## (" + RULE_ID + r") — (\S.*)$")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def registry(rules_dir=DEFAULT_RULES):
    directory = Path(rules_dir).resolve(strict=True)
    if not directory.is_dir():
        raise ValueError(f"Not a rules directory: {directory}")
    # Explicit directory only, no repository traversal. README is non-rule metadata.
    config = load_json(directory / "rule-files.json")
    names = config.get("files") if isinstance(config, dict) else None
    if (not isinstance(names, list) or not names or
            any(not isinstance(n, str) or Path(n).name != n or not n.endswith(".md") or n == "README.md" for n in names)):
        raise ValueError("rule-files.json must configure nonempty immediate Markdown file names")
    if len(set(names)) != len(names):
        raise ValueError("Duplicate configured rule file")
    discovered = {p.name for p in directory.iterdir() if p.suffix == ".md" and p.name != "README.md"}
    if set(names) != discovered:
        raise ValueError(f"Configured rule files differ from directory: missing={sorted(set(names)-discovered)}, unconfigured={sorted(discovered-set(names))}")
    paths = [directory / name for name in sorted(names)]
    if not paths:
        raise ValueError(f"No rule files in configured directory: {directory}")
    files, seen = [], set()
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Rule file must be a regular non-symlink file: {path.name}")
        raw = path.read_bytes()
        lines = raw.decode("utf-8").splitlines()
        headings = []
        for index, line in enumerate(lines):
            if re.match(r"^#+\s+" + RULE_ID + r"\b", line) and not HEADING.fullmatch(line):
                raise ValueError(f"{path.name}:{index + 1}: malformed rule heading")
            if not line.startswith("## "):
                continue
            match = HEADING.fullmatch(line)
            if match:
                headings.append((index, match.group(1), match.group(2)))
            elif line != "## Reviewer instructions":
                raise ValueError(f"{path.name}:{index + 1}: malformed rule heading; expected '## ID — Title'")
        if not headings:
            raise ValueError(f"{path.name}: no rule definitions")
        rules = []
        for pos, (index, rule_id, title) in enumerate(headings):
            end = headings[pos + 1][0] if pos + 1 < len(headings) else len(lines)
            body = "\n".join(lines[index + 1:end]).split("## Reviewer instructions")[0]
            # Support the two existing formats without rewriting IDs or rule semantics.
            generic = ("**Applies when:**", "**Violation:**", "**Default severity:**", "**Do not report when:**")
            team = ("**Applies to:**", "**Check:**", "**Default priority:**", "**Exceptions:**")
            fields = generic if "**Applies when:**" in body else team
            for field in fields:
                if not re.search(re.escape(field) + r"[ \t]*\S", body):
                    raise ValueError(f"{path.name}:{index + 1}: {rule_id} missing or empty {field}")
            if not re.search(r"\*\*Default (?:severity|priority):\*\*\s*P[0-3]\b", body):
                raise ValueError(f"{path.name}:{index + 1}: invalid default severity")
            if rule_id in seen:
                raise ValueError(f"Duplicate rule ID: {rule_id} ({path.name}:{index + 1})")
            seen.add(rule_id)
            rules.append({"id": rule_id, "title": title, "line": index + 1})
        files.append({"path": path.name, "sha256": digest(raw), "rules": rules})
    content = {"version": 1, "files": files}
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return {**content, "sha256": digest(canonical)}


def rule_ids(manifest):
    return [rule["id"] for file in manifest["files"] for rule in file["rules"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules-dir", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--review-id", help="Required when storing artifacts or supplying rule text")
    parser.add_argument("--write-artifacts", action="store_true")
    parser.add_argument("--supply", action="store_true", help="Output rule text to caller; not proof of reviewer reading")
    args = parser.parse_args()
    try:
        manifest = registry(args.rules_dir)
        if (args.write_artifacts or args.supply) and not args.review_id:
            raise ValueError("--review-id is required")
        if args.write_artifacts:
            from validators.common import write_artifact
            from validators.audit import append_event
            write_artifact("ruleset.json", manifest)
            append_event(args.review_id, "rules_registered", "registry", rule_ids(manifest),
                         {"manifest_sha256": manifest["sha256"]})
        if args.supply:
            # Recheck bytes to avoid claiming a supplied file matches a stale manifest.
            texts = []
            for file in manifest["files"]:
                raw = (args.rules_dir / file["path"]).read_bytes()
                if digest(raw) != file["sha256"]:
                    raise ValueError("Rule file changed during supply; retry registry")
                texts.append({"path": file["path"], "sha256": file["sha256"], "text": raw.decode("utf-8")})
            from validators.audit import append_event
            append_event(args.review_id, "rule_files_supplied", "registry", rule_ids(manifest),
                         {"files": [{"path": f["path"], "sha256": f["sha256"]} for f in texts],
                          "channel": "stdout", "read_confirmation": False})
            print(json.dumps({"manifest": manifest, "supplied_files": texts}, indent=2))
        else:
            print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"Registry INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
