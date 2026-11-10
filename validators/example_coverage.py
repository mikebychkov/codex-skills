"""Generate an honest, deliberately incomplete example in external review state."""
import argparse
import json
import sys
from pathlib import Path
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validators.common import external_state, write_artifact
from validators.rule_registry import registry, rule_ids
from validators.validate_coverage import summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-id', required=True)
    parser.add_argument('--change', required=True)
    args = parser.parse_args()
    try:
        repo, _ = external_state()
        manifest = registry()
        entries = [{'rule_id': rule_id, 'status': 'UNVERIFIED',
                    'reason': 'Example only: no target diff was analyzed; applicability is undetermined.',
                    'inspected': [], 'evidence': [], 'finding_ids': [],
                    'limitations': ['No semantic review was performed for this example.'],
                    'needed': ['Inspect the requested diff and evaluate applicability and relevant source.']}
                   for rule_id in rule_ids(manifest)]
        report = {'version': 1, 'review_id': args.review_id,
                  'target': {'repository': str(repo), 'change': args.change},
                  'ruleset': manifest, 'evaluations': entries, 'findings': [],
                  'limitations': ['Example declarations only; no judge or tool-read interception.'],
                  'summary': summary(entries)}
        print(write_artifact('rule-coverage-draft.json', report))
        return 0
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
