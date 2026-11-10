"""Validate reviewer declarations; structural validity is not semantic correctness."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validators.common import ROOT, load_json
from validators.rule_registry import DEFAULT_RULES, registry, rule_ids
from validators.schema_contract import validate as schema_validate

SCHEMA = ROOT / 'skills/review-merge-request/assets/rule-coverage.schema.json'
EXIT_CODES = {'VALID_COMPLETE': 0, 'VALID_INCOMPLETE': 3, 'INVALID': 2}


def summary(evaluations):
    counts = Counter(entry['status'] for entry in evaluations)
    return {'registered': len(evaluations),
            # Conservative: includes rules that may apply but remain UNVERIFIED.
            'applicable': counts['PASS'] + counts['FAIL'] + counts['UNVERIFIED'],
            'passed': counts['PASS'], 'failed': counts['FAIL'],
            'not_applicable': counts['NOT_APPLICABLE'], 'unverified': counts['UNVERIFIED'],
            'completion': 'VALID_INCOMPLETE' if counts['UNVERIFIED'] else 'VALID_COMPLETE'}


def validate_report(report, manifest):
    errors = schema_validate(report, load_json(SCHEMA))
    if errors:
        return {'classification': 'INVALID', 'errors': errors}
    if report['ruleset'] != manifest:
        errors.append('ruleset: manifest/hash mismatch against configured rule files; regenerate registry and re-evaluate changed rules')
    expected = set(rule_ids(manifest))
    entries = [entry['rule_id'] for entry in report['evaluations']]
    for rule_id, count in Counter(entries).items():
        if count != 1:
            errors.append(f'evaluations: duplicate rule ID {rule_id}')
    for missing in sorted(expected - set(entries)):
        errors.append(f'evaluations: missing rule ID {missing}')
    for unknown in sorted(set(entries) - expected):
        errors.append(f'evaluations: unknown rule ID {unknown}')
    findings = [finding['id'] for finding in report['findings']]
    if len(set(findings)) != len(findings):
        errors.append('findings: duplicate finding IDs')
    for entry in report['evaluations']:
        for finding_id in entry['finding_ids']:
            if finding_id not in findings:
                errors.append(f'{entry["rule_id"]}: unknown finding reference {finding_id}')
        for location in entry['inspected']:
            check_location(location, errors, entry['rule_id'])
    for finding in report['findings']:
        for location in finding['locations']:
            check_location(location, errors, finding['id'])
    calculated = summary(report['evaluations'])
    for key, value in calculated.items():
        if report['summary'][key] != value:
            errors.append(f'summary.{key}: expected {value!r}, got {report["summary"][key]!r}')
    return {'classification': 'INVALID' if errors else calculated['completion'],
            'errors': sorted(errors)}


def check_location(location, errors, label):
    if ('start_line' in location) != ('end_line' in location):
        errors.append(f'{label}: both start_line and end_line required when specifying a range')
    if location.get('end_line', 1) < location.get('start_line', 1):
        errors.append(f'{label}: reversed line range')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--rules-dir', type=Path, default=DEFAULT_RULES)
    parser.add_argument('--write-artifacts', action='store_true', help='Store report, result and audit in guarded REVIEW_STATE_DIR')
    args = parser.parse_args()
    try:
        report = load_json(args.report)
        manifest = registry(args.rules_dir)
        result = validate_report(report, manifest)
        if args.write_artifacts:
            from validators.common import external_state, write_artifact
            from validators.audit import append_event
            repo, state = external_state()
            identity = load_json(state / 'coverage-identity.json')
            review_id = identity['review_id']
            schema_ok = not schema_validate(report, load_json(SCHEMA))
            bound = schema_ok and report['review_id'] == review_id and Path(report['target']['repository']).resolve() == repo
            if schema_ok and not bound:
                result = {'classification': 'INVALID', 'errors': result['errors'] +
                          ['Report review ID/repository does not match guarded review identity']}
            if bound:
                for entry in report['evaluations']:
                    append_event(review_id, 'reviewer_evaluation', 'reviewer_declared',
                                 [entry['rule_id']], {'evaluation': entry})
            # Preserve invalid outcomes too; never mislabel malformed input as evaluation evidence.
            write_artifact('rule-coverage.json', report)
            write_artifact('rule-coverage-validation.json', result)
            if schema_ok:
                from validators.render_coverage import render
                with (state / 'rule-coverage.md').open('x', encoding='utf-8') as stream:
                    stream.write(render(report, result))
            append_event(review_id, 'validator_result', 'validator', rule_ids(manifest), result)
        print(json.dumps(result, indent=2))
        return EXIT_CODES[result['classification']]
    except (OSError, ValueError, KeyError, UnicodeError) as exc:
        result = {'classification': 'INVALID', 'errors': [str(exc)]}
        if args.write_artifacts:
            try:
                from validators.common import external_state
                from validators.audit import append_event
                _, state = external_state()
                identity = load_json(state / 'coverage-identity.json')
                append_event(identity['review_id'], 'validator_result', 'validator', [], result)
            except (OSError, ValueError, KeyError) as audit_error:
                result['errors'].append(f'Audit result unavailable: {audit_error}')
        print(json.dumps(result))
        return 2


if __name__ == '__main__':
    sys.exit(main())
