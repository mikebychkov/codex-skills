"""Adapter tests use synthetic XML; real-JAR tests are explicitly skipped if absent."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from validators.common import ROOT
from validators.rule_registry import registry, rule_ids
from validators.validate_coverage import validate_report, summary

spec = importlib.util.spec_from_file_location('checkstyle_adapter', ROOT / 'static-analysis/run_checkstyle.py')
sa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sa)


def xml_executor(errors=None, omit=None, status=None):
    def execute(argv, **kwargs):
        root = ET.Element('checkstyle', version='14.4.0')
        for filename in argv[argv.index('xml') + 1:]:
            name = Path(filename).name
            if name == omit:
                continue
            node = ET.SubElement(root, 'file', name=filename)
            for rule, line, column in (errors or {}).get(name, []):
                source = next((k for k, v in sa.SOURCES.items() if v == rule), rule)
                ET.SubElement(node, 'error', line=str(line), column=str(column),
                              severity='error', message='fixture', source=source)
        count = sum(len(node) for node in root)
        return subprocess.CompletedProcess(argv, count if status is None else status,
                                           ET.tostring(root), b'')
    return execute


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'; self.repo.mkdir()
        self.work = self.root / 'export'; self.work.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        self.write('A.java', 'class A {\n  int old;\n}\n')
        self.commit()
        self.base = self.git('rev-parse', 'HEAD').strip()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.DEVNULL).decode()

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')

    def analyze(self, errors=None, executor=None, verifier=None):
        return sa.analyze(self.repo, 'HEAD', self.base, self.work,
                          executor=executor or xml_executor(errors),
                          verifier=verifier or (lambda: ('14.4.0', 'a' * 64)))

    def states(self, result):
        return {e['rule_id']: e['status'] for e in result['evaluations']}

    def test_modified_file_line_mapping_and_old_static_import(self):
        self.write('A.java', 'import static a.B.c;\nclass A {\n  int old;\n}\n')
        self.commit(); self.base = self.git('rev-parse', 'HEAD').strip()
        self.write('A.java', 'import static a.B.c;\nclass A {\n  int old;\n  java.util.List value;\n}\n')
        self.commit()
        result = self.analyze({'A.java': [(sa.RULES[0], 1, 1), (sa.RULES[1], 4, 12)]})
        self.assertEqual(self.states(result), dict(zip(sa.RULES, ['PASS', 'FAIL'])))
        self.assertEqual(result['findings'][0]['locations'][0]['start_line'], 4)
        self.assertEqual(result['diagnostics'][0]['analysis_status'], 'OUTSIDE_CHANGED_LINES')

    def test_new_java_file_static_import(self):
        self.write('New.java', 'import static a.B.c;\nclass New {}\n'); self.commit()
        result = self.analyze({'New.java': [(sa.RULES[0], 1, 1)]})
        self.assertEqual(self.states(result)[sa.RULES[0]], 'FAIL')
        self.assertEqual(result['files'][0]['ranges'], [(1, 2)])

    def test_quoted_and_unicode_path_attribution(self):
        name = 'odd "directory/Ü.java'
        self.write(name, 'import static a.B.c;\nclass Example {}\n'); self.commit()
        result = self.analyze({'Ü.java': [(sa.RULES[0], 1, 1)]})
        self.assertEqual(result['findings'][0]['locations'][0]['file'], name)
        self.assertEqual(self.states(result)[sa.RULES[0]], 'FAIL')

    def test_rename_only_no_introduced_lines(self):
        self.git('mv', 'A.java', 'Renamed.java'); self.commit()
        result = self.analyze()
        self.assertTrue(all(v == 'NOT_APPLICABLE' for v in self.states(result).values()))

    def test_rename_modified(self):
        self.write('A.java', 'class A {\n' + '  int v;\n' * 20 + '}\n'); self.commit()
        self.base = self.git('rev-parse', 'HEAD').strip()
        self.git('mv', 'A.java', 'Renamed.java')
        self.write('Renamed.java', 'class A {\n  java.util.List x;\n' + '  int v;\n' * 20 + '}\n'); self.commit()
        result = self.analyze({'Renamed.java': [(sa.RULES[1], 2, 12)]})
        self.assertTrue(result['files'][0]['status'].startswith('R'))
        self.assertEqual(result['findings'][0]['locations'][0]['file'], 'Renamed.java')

    def test_deleted_file(self):
        self.git('rm', 'A.java'); self.commit()
        self.assertEqual(self.states(self.analyze())[sa.RULES[0]], 'NOT_APPLICABLE')

    def test_binary_java_is_unverified(self):
        (self.repo / 'A.java').write_bytes(b'class A {\x00binary}'); self.commit()
        self.assertEqual(set(self.states(self.analyze()).values()), {'UNVERIFIED'})

    @unittest.skipUnless(hasattr(os, 'symlink'), 'Symlinks unavailable')
    def test_symlink_java_is_not_followed(self):
        (self.repo / 'Link.java').symlink_to('A.java'); self.commit()
        self.assertEqual(set(self.states(self.analyze()).values()), {'UNVERIFIED'})

    def test_no_java_changes_does_not_require_jar(self):
        self.write('readme', 'text'); self.commit()
        verifier = lambda: self.fail('Must not launch Checkstyle without Java changes')
        self.assertEqual(self.states(self.analyze(verifier=verifier))[sa.RULES[1]], 'NOT_APPLICABLE')

    def changed(self):
        self.write('A.java', 'class A { int changed; }\n'); self.commit()

    def test_missing_distribution(self):
        self.changed()
        with patch.object(sa, 'JAR', self.root / 'missing.jar'):
            result = self.analyze(verifier=sa.verify_distribution)
        self.assertEqual(set(self.states(result).values()), {'UNVERIFIED'})
        self.assertFalse(result['findings'])

    def test_execution_failure(self):
        self.changed()
        result = self.analyze(executor=lambda *a, **k: subprocess.CompletedProcess([], 1, b'', b'sensitive'))
        self.assertEqual(set(self.states(result).values()), {'UNVERIFIED'})
        self.assertNotIn('sensitive', json.dumps(result))

    def test_partial_parser_failure(self):
        self.changed(); self.write('B.java', 'invalid syntax'); self.commit()
        result = self.analyze({'A.java': [(sa.RULES[0], 1, 1)], 'B.java': [('parser.failure', 0, 0)]})
        self.assertEqual(set(self.states(result).values()), {'UNVERIFIED'})
        self.assertEqual(len(result['findings']), 1)  # confirmed result retained, incomplete coverage
        self.assertTrue(all(not e['finding_ids'] for e in result['evaluations']))

    def test_missing_file_in_xml(self):
        self.changed()
        result = self.analyze(executor=xml_executor(omit='A.java'))
        self.assertEqual(set(self.states(result).values()), {'UNVERIFIED'})

    def test_unexpected_exit_status(self):
        self.changed()
        self.assertEqual(self.states(self.analyze(executor=xml_executor(status=5)))[sa.RULES[0]], 'UNVERIFIED')

    def test_known_fqcn_gap_suppresses_speculative_finding(self):
        self.changed()
        result = self.analyze({'A.java': [(sa.LIMIT_SOURCE, 1, 1), (sa.RULES[1], 1, 8)]})
        self.assertEqual(self.states(result), dict(zip(sa.RULES, ['PASS', 'UNVERIFIED'])))
        self.assertFalse(result['findings'])
        self.assertEqual(result['diagnostics'][0]['analysis_status'], 'REQUIRES_VERIFICATION')

    def test_indirect_attribution(self):
        self.write('A.java', 'class A {\n  java.util.List old;\n  int x;\n}\n'); self.commit()
        self.base = self.git('rev-parse', 'HEAD').strip()
        self.write('A.java', 'class A {\n  java.util.List old;\n  int y;\n}\n'); self.commit()
        result = self.analyze({'A.java': [(sa.RULES[1], 2, 12)]})
        self.assertEqual(self.states(result)[sa.RULES[1]], 'UNVERIFIED')
        self.assertFalse(result['findings'])

    def test_generated_fqcn_excluded_static_import_still_checked(self):
        self.write('generated/G.java', 'import static a.B.c;\nclass G { java.util.List x; }\n'); self.commit()
        result = self.analyze({'G.java': [(sa.RULES[0], 1, 1), (sa.RULES[1], 2, 24)]})
        self.assertEqual(self.states(result)[sa.RULES[1]], 'NOT_APPLICABLE')
        self.assertEqual(self.states(result)[sa.RULES[0]], 'FAIL')

    def test_committed_blobs_only_and_read_only(self):
        self.changed()
        self.write('A.java', 'staged invalid syntax'); self.git('add', 'A.java')
        self.write('A.java', 'unstaged invalid syntax'); self.write('Untracked.java', 'untracked')
        sys.path.insert(0, str(ROOT / 'hooks'))
        from _integrity import state_snapshot
        before = state_snapshot(self.repo)
        def execute(argv, **kwargs):
            exported = [Path(p) for p in argv[argv.index('xml') + 1:]]
            self.assertEqual(len(exported), 1)
            self.assertEqual(exported[0].read_text(), 'class A { int changed; }\n')
            self.assertNotEqual(Path(kwargs['cwd']), self.repo)
            return xml_executor()(argv, **kwargs)
        result = self.analyze(executor=execute)
        self.assertEqual(result['analysis_status'], 'COMPLETE')
        self.assertEqual(state_snapshot(self.repo), before)
        self.assertEqual((self.repo / 'Untracked.java').read_text(), 'untracked')

    def test_one_batch_for_multiple_files(self):
        self.changed(); self.write('B.java', 'class B {}'); self.commit()
        calls = []
        def execute(argv, **kwargs):
            calls.append(argv)
            return xml_executor()(argv, **kwargs)
        self.analyze(executor=execute)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0][calls[0].index('xml') + 1:]), 2)

    def test_missing_ref_is_unverified(self):
        self.base = 'missing-ref'
        self.assertEqual(set(self.states(self.analyze()).values()), {'UNVERIFIED'})

    def test_coverage_integration_all_statuses(self):
        self.changed()
        for errors in [None, {'A.java': [(sa.RULES[0], 1, 1)]}, {'A.java': [('parser.failure', 0, 0)]}]:
            # separate export dirs because analyze never overwrites input paths
            with tempfile.TemporaryDirectory(dir=self.root) as work:
                self.work = Path(work)
                result = self.analyze(errors)
            manifest = registry()
            entries = [{'rule_id': rid, 'status': 'UNVERIFIED', 'reason': 'Not reviewed',
                        'inspected': [], 'evidence': [], 'finding_ids': [], 'limitations': ['No review'],
                        'needed': ['Review diff']} for rid in rule_ids(manifest)]
            report = {'version': 1, 'review_id': 'fixture', 'target': result['target'],
                      'ruleset': manifest, 'evaluations': entries, 'findings': [],
                      'limitations': [], 'summary': summary(entries)}
            merged = sa.merge_coverage(report, result)
            self.assertEqual(validate_report(merged, manifest)['classification'], 'VALID_INCOMPLETE')

    def test_offline_command_environment(self):
        with patch.object(sa.subprocess, 'run') as mocked:
            with patch.dict(os.environ, {'JAVA_TOOL_OPTIONS': '-javaagent:evil', 'JDK_JAVA_OPTIONS': 'bad'}):
                sa.run(['java', '-jar', 'bundled.jar'])
            argv = mocked.call_args.args[0]
            env = mocked.call_args.kwargs['env']
            self.assertEqual(argv, ['java', '-jar', 'bundled.jar'])
            self.assertNotIn('JAVA_TOOL_OPTIONS', env)
            self.assertNotIn('JDK_JAVA_OPTIONS', env)
            self.assertEqual(env['GIT_OPTIONAL_LOCKS'], '0')

    def test_cli_external_cwd_artifacts_and_audit(self):
        self.changed()
        state = self.root / 'review-state'
        env = {**os.environ, 'TARGET_REPO': str(self.repo), 'REVIEW_STATE_DIR': str(state),
               'PYTHONDONTWRITEBYTECODE': '1'}
        subprocess.run([sys.executable, str(ROOT / 'hooks/init-review/hook.py')],
                       env=env, cwd=self.root, check=True, capture_output=True)
        proc = subprocess.run([sys.executable, str(sa.HERE / 'run_checkstyle.py'),
                               '--source', 'HEAD', '--target', self.base, '--review-id', 'fixture'],
                              env=env, cwd=self.root, capture_output=True)
        self.assertIn(proc.returncode, (0, 3), proc.stderr)
        result = json.loads((state / 'static-analysis-results.json').read_text())
        self.assertEqual(result['review_id'], 'fixture')
        if not sa.JAR.is_file():
            self.assertEqual(set(self.states(result).values()), {'UNVERIFIED'})
        events = [json.loads(line) for line in (state / 'rule-coverage-audit.jsonl').read_text().splitlines()]
        self.assertEqual([e['event_type'] for e in events], ['static_analysis_started', 'static_analysis_result'])
        self.assertTrue(all(e['source'] == 'static_analyzer' for e in events))
        verify = subprocess.run([sys.executable, str(ROOT / 'hooks/verify-working-tree/hook.py')],
                                env=env, cwd=self.root, capture_output=True)
        self.assertEqual(verify.returncode, 0, verify.stderr)
        # Running twice cannot overwrite the original artifact.
        again = subprocess.run([sys.executable, str(sa.HERE / 'run_checkstyle.py'),
                                '--source', 'HEAD', '--target', self.base, '--review-id', 'fixture'],
                               env=env, cwd=self.root, capture_output=True)
        self.assertEqual(again.returncode, 2)
        self.assertEqual(json.loads((state / 'static-analysis-results.json').read_text()), result)

    def test_coverage_target_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, 'scope/repository'):
            sa.merge_coverage({'target': {'change': 'wrong'}}, {'target': {'change': 'right'}})

    def test_explicit_generated_path_exclusion(self):
        self.write('A.java', 'class A { java.util.List x; }\n'); self.commit()
        result = sa.analyze(self.repo, 'HEAD', self.base, self.work,
                            executor=xml_executor({'A.java': [(sa.RULES[1], 1, 18)]}),
                            verifier=lambda: ('14.4.0', 'a' * 64), generated_paths=['A.java'])
        self.assertEqual(self.states(result)[sa.RULES[1]], 'NOT_APPLICABLE')
        self.assertFalse(result['findings'])
        self.assertTrue(result['files'][0]['generated'])

    def test_generated_only_missing_jar_does_not_claim_fqcn_applicability(self):
        self.write('generated/A.java', 'class A {}\n'); self.git('rm', 'A.java'); self.commit()
        with patch.object(sa, 'JAR', self.root / 'missing.jar'):
            result = self.analyze(verifier=sa.verify_distribution)
        self.assertEqual(self.states(result), dict(zip(sa.RULES, ['UNVERIFIED', 'NOT_APPLICABLE'])))

    def test_high_violation_count_exit_mapping(self):
        self.changed()
        errors = {'A.java': [(sa.RULES[0], 1, i + 1) for i in range(256)]}
        result = self.analyze(executor=xml_executor(errors, status=0 if os.name == 'posix' else 256))
        self.assertEqual(self.states(result)[sa.RULES[0]], 'FAIL')
        self.assertEqual(len(result['findings']), 256)

    def test_integrity_change_stops_publication_without_revert(self):
        state = self.root / 'review-state'
        env = {'TARGET_REPO': str(self.repo), 'REVIEW_STATE_DIR': str(state),
               'PYTHONDONTWRITEBYTECODE': '1'}
        subprocess.run([sys.executable, str(ROOT / 'hooks/init-review/hook.py')],
                       env={**os.environ, **env}, check=True, capture_output=True)
        def unexpected_change(*args, **kwargs):
            self.write('A.java', 'unexpected modification')
            return {}
        with patch.dict(os.environ, env), patch.object(sys, 'argv', [str(sa.HERE / 'run_checkstyle.py'),
                '--source', 'HEAD', '--target', self.base, '--review-id', 'fixture']), \
                patch.object(sa, 'analyze', unexpected_change):
            self.assertEqual(sa.main(), 2)
        self.assertFalse((state / 'static-analysis-results.json').exists())
        self.assertEqual((self.repo / 'A.java').read_text(), 'unexpected modification')

    def test_missing_checksum_and_corrupt_distribution(self):
        candidate = self.root / 'checkstyle.jar'
        candidate.write_bytes(b'not a jar')
        pin = self.root / 'pin.json'
        pin.write_text(json.dumps({'version': '14.4.0', 'sha256': None}))
        with patch.object(sa, 'JAR', candidate), patch.object(sa, 'PIN', pin):
            with self.assertRaisesRegex(ValueError, 'checksum'):
                sa.verify_distribution()
            pin.write_text(json.dumps({'version': '14.4.0', 'sha256': sa.hashlib.sha256(candidate.read_bytes()).hexdigest()}))
            with self.assertRaises(sa.zipfile.BadZipFile):
                sa.verify_distribution()


@unittest.skipUnless(sa.JAR.is_file(), 'Bundled all-in-one JAR unavailable: real Checkstyle integration NOT RUN')
class RealCheckstyleTests(unittest.TestCase):
    """Real behavior tests never use mocked analyzer output or dependency downloads."""
    setUp = AdapterTests.setUp
    git = AdapterTests.git
    write = AdapterTests.write
    commit = AdapterTests.commit
    changed = AdapterTests.changed
    states = AdapterTests.states
    def actual(self, text):
        self.write('A.java', text); self.commit()
        with tempfile.TemporaryDirectory(dir=self.root) as work:
            return sa.analyze(self.repo, 'HEAD', self.base, work)

    def test_actual_supported_and_ignored_forms(self):
        cases = {
            'variable': ('class A { java.util.List x; }', True),
            'return': ('class A { java.util.List f() { return null; } }', True),
            'constructor': ('class A { Object x = new java.util.ArrayList(); }', True),
            'import': ('import java.util.List; class A { List x; }', False),
            'package': ('package java.example; class A {}', False),
            'string': ('class A { String x = "java.util.List"; }', False),
            'comment': ('/** java.util.List */ class A { /* java.util.List */ }', False),
            'conflict': ('class A { java.util.Date a; java.sql.Date b; }', False),
        }
        for name, (text, violation) in cases.items():
            with self.subTest(name=name):
                result = self.actual(text + '\n')
                self.assertEqual(self.states(result)[sa.RULES[1]], 'FAIL' if violation else 'PASS', result)

    def test_actual_annotation_class_reference_is_gap(self):
        result = self.actual('@java.lang.Deprecated class A {}\n')
        self.assertEqual(self.states(result)[sa.RULES[1]], 'UNVERIFIED', result)
        self.assertFalse(result['findings'])

    def test_actual_class_literal_in_annotation_is_gap(self):
        result = self.actual('@Example(java.lang.String.class) class A {}\n')
        self.assertEqual(self.states(result)[sa.RULES[1]], 'UNVERIFIED', result)
        self.assertFalse(result['findings'])

    def test_actual_static_import(self):
        result = self.actual('import static java.util.Collections.emptyList;\nclass A {}\n')
        self.assertEqual(self.states(result)[sa.RULES[0]], 'FAIL', result)

    def test_actual_parser_failure(self):
        result = self.actual('class A { invalid syntax !!!!! }\n')
        self.assertEqual(set(self.states(result).values()), {'UNVERIFIED'}, result)

    def test_actual_distribution_from_other_cwd(self):
        # Invokes the absolute adapter from a cwd unrelated to review-system.
        self.changed()
        state2 = self.root / 'state2'
        env = {**os.environ, 'TARGET_REPO': str(self.repo), 'REVIEW_STATE_DIR': str(state2),
               'PYTHONDONTWRITEBYTECODE': '1'}
        subprocess.run([sys.executable, str(ROOT / 'hooks/init-review/hook.py')], env=env, cwd=self.root, check=True, capture_output=True)
        proc = subprocess.run([sys.executable, str(sa.HERE / 'run_checkstyle.py'), '--source', 'HEAD',
                               '--target', self.base, '--review-id', 'real'], env=env, cwd=self.root, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads((state2 / 'static-analysis-results.json').read_text())
        self.assertEqual(report['analysis_status'], 'COMPLETE')
