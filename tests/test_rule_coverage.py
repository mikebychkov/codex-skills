import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from validators.common import ROOT, load_json, write_artifact
from validators.rule_registry import registry, rule_ids
from validators.validate_coverage import validate_report, summary, SCHEMA
from validators.schema_contract import validate as schema_validate
from validators.audit import append_event
from validators.render_coverage import render

BODY = '''\n**Applies when:** public contracts change.
**Violation:** incompatible API change.
**Default severity:** P2.
**Do not report when:** explicitly versioned.
'''


def fixture_rules(directory):
    (directory / 'rule-files.json').write_text(json.dumps({'files': ['a.md', 'b.md']}))
    (directory / 'a.md').write_text('## GENERIC-001 — Contract\n' + BODY)
    (directory / 'b.md').write_text('## GENERIC-002 — Errors\n' + BODY)
    return registry(directory)


def report_for(manifest):
    evaluations = [{'rule_id': rule_id, 'status': 'PASS',
                    'reason': 'Compared changed signature with both callers and versioned contract.',
                    'inspected': [{'file': 'src/Api.java', 'start_line': 10, 'end_line': 15}],
                    'evidence': ['Both callers retain matching argument types and error mapping.'],
                    'finding_ids': [], 'limitations': [], 'needed': []}
                   for rule_id in rule_ids(manifest)]
    return {'version': 1, 'review_id': 'test-review',
            'target': {'repository': '/synthetic/fixture', 'change': 'base...head'},
            'ruleset': manifest, 'evaluations': evaluations, 'findings': [],
            'limitations': [], 'summary': summary(evaluations)}


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.rules = Path(self.temp.name)
        self.manifest = fixture_rules(self.rules)
        self.report = report_for(self.manifest)

    def outcome(self):
        return validate_report(self.report, self.manifest)['classification']

    def test_valid_complete(self):
        self.assertEqual(self.outcome(), 'VALID_COMPLETE')

    def test_unverified_incomplete(self):
        entry = self.report['evaluations'][0]
        entry.update(status='UNVERIFIED', inspected=[], evidence=[], limitations=['Missing dependency source'], needed=['Read dependency implementation'])
        self.report['summary'] = summary(self.report['evaluations'])
        self.assertEqual(self.outcome(), 'VALID_INCOMPLETE')

    def test_missing_rule(self):
        self.report['evaluations'].pop()
        self.report['summary'] = summary(self.report['evaluations'])
        self.assertEqual(self.outcome(), 'INVALID')

    def test_unknown_rule(self):
        self.report['evaluations'][0]['rule_id'] = 'UNKNOWN-001'
        self.assertEqual(self.outcome(), 'INVALID')

    def test_duplicate_rule(self):
        self.report['evaluations'].append(copy.deepcopy(self.report['evaluations'][0]))
        self.report['summary'] = summary(self.report['evaluations'])
        self.assertEqual(self.outcome(), 'INVALID')

    def test_invalid_status(self):
        self.report['evaluations'][0]['status'] = 'SKIPPED'
        self.assertEqual(self.outcome(), 'INVALID')

    def test_pass_without_evidence(self):
        self.report['evaluations'][0]['evidence'] = []
        self.assertEqual(self.outcome(), 'INVALID')

    def test_pass_without_inspected(self):
        self.report['evaluations'][0]['inspected'] = []
        self.assertEqual(self.outcome(), 'INVALID')

    def test_fail_without_finding(self):
        self.report['evaluations'][0]['status'] = 'FAIL'
        self.report['summary'] = summary(self.report['evaluations'])
        self.assertEqual(self.outcome(), 'INVALID')

    def fail_entry(self, ids):
        self.report['evaluations'][0].update(status='FAIL', finding_ids=ids)
        self.report['summary'] = summary(self.report['evaluations'])

    def test_unknown_finding(self):
        self.fail_entry(['F404'])
        self.assertEqual(self.outcome(), 'INVALID')

    def test_not_applicable_without_reason(self):
        self.report['evaluations'][0].update(status='NOT_APPLICABLE', reason='')
        self.report['summary'] = summary(self.report['evaluations'])
        self.assertEqual(self.outcome(), 'INVALID')

    def test_unverified_without_explanation(self):
        self.report['evaluations'][0].update(status='UNVERIFIED', reason='')
        self.report['summary'] = summary(self.report['evaluations'])
        self.assertEqual(self.outcome(), 'INVALID')

    def test_unverified_without_needed_checks(self):
        self.report['evaluations'][0].update(status='UNVERIFIED', limitations=['No source'])
        self.report['summary'] = summary(self.report['evaluations'])
        self.assertEqual(self.outcome(), 'INVALID')

    def test_summary_wrong(self):
        self.report['summary']['passed'] = 99
        self.assertEqual(self.outcome(), 'INVALID')

    def test_hash_modified(self):
        self.report['ruleset'] = copy.deepcopy(self.manifest)
        self.report['ruleset']['files'][0]['sha256'] = '0' * 64
        self.assertEqual(self.outcome(), 'INVALID')

    def test_live_rule_changed(self):
        (self.rules / 'a.md').write_text((self.rules / 'a.md').read_text() + '\nChanged exception.\n')
        self.assertEqual(validate_report(self.report, registry(self.rules))['classification'], 'INVALID')

    def test_registry_duplicate_across_files(self):
        (self.rules / 'b.md').write_text('## GENERIC-001 — Duplicate\n' + BODY)
        with self.assertRaisesRegex(ValueError, 'Duplicate rule ID'):
            registry(self.rules)

    def test_malformed_definition(self):
        for malformed in ['## GENERIC-001 - Wrong delimiter\n' + BODY,
                          '## GENERIC-001 — Missing fields\n',
                          '### GENERIC-001 — Wrong level\n' + BODY,
                          '## BROKEN-1 — Invalid ID\n' + BODY,
                          '## GENERIC-001 — Empty applicability\n' + BODY.replace('public contracts change.', '')]:
            with self.subTest(malformed=malformed):
                (self.rules / 'a.md').write_text(malformed)
                with self.assertRaises(ValueError):
                    registry(self.rules)

    def test_deterministic_multiple_files(self):
        self.assertEqual(self.manifest, registry(self.rules))
        (self.rules / 'rule-files.json').write_text(json.dumps({'files': ['b.md', 'a.md']}))
        self.assertEqual(self.manifest, registry(self.rules))
        self.assertEqual([f['path'] for f in self.manifest['files']], ['a.md', 'b.md'])

    def test_missing_configured_file(self):
        (self.rules / 'b.md').unlink()
        with self.assertRaisesRegex(ValueError, 'missing='):
            registry(self.rules)

    def test_unconfigured_file(self):
        (self.rules / 'c.md').write_text('## GENERIC-003 — Extra\n' + BODY)
        with self.assertRaisesRegex(ValueError, 'unconfigured='):
            registry(self.rules)

    def test_multiple_findings(self):
        self.fail_entry(['F001', 'F002'])
        self.report['findings'] = [{'id': i, 'priority': 'P2', 'title': 'Concrete incompatible API',
                                   'locations': [{'file': 'src/Api.java', 'start_line': 10, 'end_line': 12}],
                                   'evidence': ['New signature no longer accepts caller input.']}
                                  for i in ['F001', 'F002']]
        self.assertEqual(self.outcome(), 'VALID_COMPLETE')

    def test_reversed_range(self):
        self.report['evaluations'][0]['inspected'][0]['end_line'] = 1
        self.assertEqual(self.outcome(), 'INVALID')

    def test_whitespace_evidence(self):
        self.report['evaluations'][0]['evidence'] = ['  ']
        self.assertEqual(self.outcome(), 'INVALID')

    def test_schema_unknown_field_and_bool_total(self):
        self.report['summary']['passed'] = True
        self.report['unexpected'] = 'field'
        self.assertEqual(self.outcome(), 'INVALID')

    def test_unknown_schema_keyword_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            schema_validate({}, {'unsupported': 1})

    def test_duplicate_json_keys(self):
        path = self.rules / 'input.json'
        path.write_text('{"review_id":"a","review_id":"b"}')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
            load_json(path)

    def test_actual_rules(self):
        actual = registry()
        self.assertEqual(len(rule_ids(actual)), 22)
        self.assertEqual(actual, registry())
        self.assertEqual(validate_report(report_for(actual), actual)['classification'], 'VALID_COMPLETE')

    def test_output_contract(self):
        contract = (ROOT / 'skills/review-merge-request/assets/output-format.md').read_text()
        for section in ['Review verdict', 'Findings', 'Pre-existing observations', 'Commands executed',
                        'Validation results', 'Validation limitations', 'Working-tree status', 'Rule Coverage Report']:
            self.assertIn(section, contract)
        self.assertIn('No project files were intentionally modified during this review.', contract)
        text = render(self.report, validate_report(self.report, self.manifest))
        self.assertIn('| Rule ID | Status | Evidence / Reason |', text)
        for rule_id in rule_ids(self.manifest):
            self.assertIn(f'| {rule_id} | PASS |', text)
        self.assertIn('not semantic verification', text)


class ExternalStateAndHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'synthetic-repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture')
        self.state = self.base / 'state'
        self.env = {**os.environ, 'TARGET_REPO': str(self.repo), 'REVIEW_STATE_DIR': str(self.state),
                    'PYTHONDONTWRITEBYTECODE': '1', 'MAVEN_SETTINGS': ''}
        self.patcher = patch.dict(os.environ, self.env)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.assertEqual(self.hook('init-review').returncode, 0)

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True)

    def hook(self, name):
        return subprocess.run([sys.executable, str(ROOT / 'hooks' / name / 'hook.py')],
                              env=self.env, capture_output=True, text=True)

    def test_hook_lifecycle_and_settings(self):
        self.assertEqual(self.hook('before-validation').returncode, 3)
        self.assertEqual(self.hook('after-validation').returncode, 0)
        self.assertEqual(self.hook('verify-working-tree').returncode, 0)
        self.assertEqual(self.hook('init-review').returncode, 12)

    def test_artifact_outside_repo_and_exclusive(self):
        output = write_artifact('example.json', {'fixture': True})
        self.assertEqual(output.parent, self.state.resolve())
        with self.assertRaises(FileExistsError):
            write_artifact('example.json', {})
        self.assertEqual(self.hook('verify-working-tree').returncode, 0)

    def test_artifact_rejects_target_path(self):
        with patch.dict(os.environ, {'REVIEW_STATE_DIR': str(self.repo / 'state')}):
            with self.assertRaisesRegex(ValueError, 'overlaps'):
                write_artifact('example.json', {})

    def test_audit_provenance(self):
        event = append_event('test', 'rules_registered', 'registry', ['GENERIC-001'], {})
        self.assertIn('timestamp', event)
        with self.assertRaises(ValueError):
            append_event('test', 'tool_read_confirmed', 'harness_observed', [], {})
        with self.assertRaises(ValueError):
            append_event('test', 'judge_result', 'judge_assessment', [], {})
        with self.assertRaises(ValueError):
            append_event('other', 'validator_result', 'validator', [], {})
        events = (self.state / 'rule-coverage-audit.jsonl').read_text().splitlines()
        self.assertEqual(len(events), 1)


    def test_path_traversal_rejected(self):
        for name in ('../escaped.json', '/tmp/escaped.json', '..'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                write_artifact(name, {})

    def test_symlink_artifact_rejected(self):
        destination = self.repo / 'untouched.json'
        (self.state / 'example.json').symlink_to(destination)
        with self.assertRaises(FileExistsError):
            write_artifact('example.json', {})
        self.assertFalse(destination.exists())

    def test_integrity_detects_mutation_in_synthetic_fixture(self):
        self.git('config', 'fixture.changed', 'true')
        self.assertEqual(self.hook('after-validation').returncode, 10)
        self.assertEqual(self.hook('verify-working-tree').returncode, 10)


    def test_invalid_schema_result_is_audited(self):
        append_event('test-review', 'rules_registered', 'registry', [], {})
        path = self.state / 'malformed-report.json'
        path.write_text('{}')
        result = subprocess.run([sys.executable, str(ROOT / 'validators/validate_coverage.py'),
                                 str(path), '--write-artifacts'], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        events = [json.loads(line) for line in (self.state / 'rule-coverage-audit.jsonl').read_text().splitlines()]
        self.assertEqual(events[-1]['event_type'], 'validator_result')
        self.assertEqual(events[-1]['details']['classification'], 'INVALID')
        self.assertNotIn('reviewer_evaluation', [event['event_type'] for event in events])


    def test_linked_worktree_git_paths_rejected(self):
        linked = self.base / 'linked'
        self.git('worktree', 'add', '--detach', str(linked), 'HEAD')
        gitdir = Path(self.git('rev-parse', '--absolute-git-dir').stdout.decode().strip())
        unsafe = gitdir / 'forbidden-state'
        env = {**self.env, 'TARGET_REPO': str(linked), 'REVIEW_STATE_DIR': str(unsafe)}
        result = subprocess.run([sys.executable, str(ROOT / 'hooks/init-review/hook.py')],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 12)
        self.assertFalse(unsafe.exists())

    def test_existing_runner_missing_settings(self):
        env = {**self.env, 'REVIEW_SYSTEM': str(ROOT), 'REVIEW_STATE_DIR': str(self.base / 'runner-state')}
        result = subprocess.run([sys.executable, str(ROOT / 'environment/example-validation-run.py')],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('UNCHANGED', result.stdout)

    def test_existing_runner_preserves_validation_failure(self):
        # A synthetic wrapper, not Maven and not a target project's wrapper.
        wrapper = self.repo / 'mvnw'
        wrapper.write_text('#!/bin/sh\nexit 7\n')
        wrapper.chmod(0o700)
        settings = self.base / 'fixture-settings.xml'
        settings.write_text('<settings/>')
        env = {**self.env, 'REVIEW_SYSTEM': str(ROOT), 'MAVEN_SETTINGS': str(settings),
               'REVIEW_STATE_DIR': str(self.base / 'runner-state')}
        result = subprocess.run([sys.executable, str(ROOT / 'environment/example-validation-run.py')],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertIn('after-validation: tracked content and checked Git state UNCHANGED', result.stdout)
        self.assertIn('Working-tree status: tracked content and checked Git state UNCHANGED', result.stdout)

    def test_cli_end_to_end(self):
        run = lambda *args: subprocess.run([sys.executable, *args], cwd=ROOT, env=self.env, capture_output=True, text=True)
        reg = run('validators/rule_registry.py', '--review-id', 'example', '--write-artifacts', '--supply')
        self.assertEqual(reg.returncode, 0, reg.stderr)
        example = run('validators/example_coverage.py', '--review-id', 'example', '--change', 'synthetic-example')
        self.assertEqual(example.returncode, 0, example.stderr)
        validated = run('validators/validate_coverage.py', str(self.state / 'rule-coverage-draft.json'), '--write-artifacts')
        self.assertEqual(validated.returncode, 3, validated.stdout + validated.stderr)
        self.assertEqual(json.loads(validated.stdout)['classification'], 'VALID_INCOMPLETE')
        self.assertTrue((self.state / 'rule-coverage.md').is_file())
        events = [json.loads(line) for line in (self.state / 'rule-coverage-audit.jsonl').read_text().splitlines()]
        types = {event['event_type'] for event in events}
        self.assertEqual(types, {'rules_registered', 'rule_files_supplied', 'reviewer_evaluation', 'validator_result'})
        self.assertEqual(self.hook('verify-working-tree').returncode, 0)


if __name__ == '__main__':
    unittest.main()
