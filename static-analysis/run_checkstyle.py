#!/usr/bin/env python3
"""Offline, committed merge-base analysis. Writes only guarded external artifacts."""
import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import time
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validators.common import external_state, write_artifact, load_json
from validators.audit import append_event
sys.path.insert(0, str(ROOT / 'hooks'))
from _integrity import HookError

HERE = Path(__file__).resolve().parent
JAR = HERE / 'checkstyle/jar/checkstyle.jar'
CONFIG = HERE / 'checkstyle/checkstyle.xml'
PIN = HERE / 'checkstyle/distribution.json'
RULES = ('JAVA-STYLE-001', 'JAVA-STYLE-002')
SOURCES = {
    'com.puppycrawl.tools.checkstyle.checks.imports.AvoidStaticImportCheck': RULES[0],
    'com.puppycrawl.tools.checkstyle.checks.imports.UnnecessaryFullyQualifiedTypeCheck': RULES[1],
}
LIMIT_SOURCE = 'com.puppycrawl.tools.checkstyle.checks.coding.MatchXpathCheck'


def run(argv, **kwargs):
    # No shell, project scripts, Java agents or inherited tool-injection options.
    env = {k: v for k, v in os.environ.items() if k not in
           ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS', 'CLASSPATH')}
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')
    if argv[0] == 'git':
        env.update(LC_ALL='C', LANG='C')
        argv = [argv[0], '-c', 'protocol.allow=never', *argv[1:]]
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=120, env=env, **kwargs)


def git(repo, *args):
    result = run(['git', '--no-optional-locks', '-C', str(repo), *args])
    if result.returncode:
        raise ValueError('Local Git comparison unavailable; no network attempted')
    return result.stdout


def resolve(repo, ref):
    return git(repo, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}').decode().strip()


def changes(repo, source, target):
    head, target_commit = resolve(repo, source), resolve(repo, target)
    base = git(repo, 'merge-base', target_commit, head).decode().strip()
    opts = ['--no-ext-diff', '--no-textconv', '--find-renames', base, head, '--', '*.java']
    raw = git(repo, 'diff', '--name-status', '-z', *opts).split(b'\0')
    files = []
    i = 0
    while i < len(raw) and raw[i]:
        status = raw[i].decode('ascii'); i += 1
        old = os.fsdecode(raw[i]); i += 1
        new = old
        if status[0] in 'RC':
            new = os.fsdecode(raw[i]); i += 1
        files.append({'status': status, 'old': old, 'file': new, 'ranges': []})
    # Pair patch sections with name-status order; filenames may be Git-quoted.
    patch = git(repo, 'diff', '--unified=0', *opts).decode('utf-8', errors='replace')
    sections = re.split(r'^diff --git .*\n', patch, flags=re.M)[1:]
    if len(sections) != len(files):
        raise ValueError('Diff attribution incomplete')
    for item, section in zip(files, sections):
        for match in re.finditer(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', section, re.M):
            start, count = int(match[1]), int(match[2] if match[2] is not None else 1)
            if count:
                item['ranges'].append((start, start + count - 1))
        item['binary'] = 'Binary files ' in section or 'GIT binary patch' in section
    return {'source': head, 'target': target_commit, 'merge_base': base,
            'comparison': f'{base}..{head}', 'requested': f'{target}...{source}'}, files


def generated(path):
    return bool(set(PurePosixPath(path).parts) & {'generated', 'generated-sources', 'generated-test-sources'})


def committed_blobs(repo, commit, items):
    """Batch metadata and blob reads; no per-file subprocess or worktree access."""
    records = git(repo, 'ls-tree', '-r', '-z', commit, '--', *[f['file'] for f in items])
    entries = {}
    for record in records.split(b'\0'):
        if record:
            header, path = record.split(b'\t', 1)
            mode, kind, oid = header.split()
            entries[os.fsdecode(path)] = (mode, kind, oid)
    selected = []
    blobs = {}
    for item in items:
        mode, kind, oid = entries[item['file']]
        if mode not in (b'100644', b'100755') or kind != b'blob' or item['binary']:
            blobs[item['file']] = None
        else:
            selected.append((item['file'], oid))
    if selected:
        output = run(['git', '--no-optional-locks', '-C', str(repo), 'cat-file', '--batch'],
                     input=b''.join(oid + b'\n' for _, oid in selected))
        if output.returncode:
            raise ValueError('Committed source blobs unavailable offline')
        offset = 0
        for path, oid in selected:
            end = output.stdout.find(b'\n', offset)
            header = output.stdout[offset:end].split()
            if end < 0 or len(header) != 3 or header[:2] != [oid, b'blob']:
                raise ValueError('Incomplete committed source blob batch')
            size = int(header[2]); offset = end + 1
            blob = output.stdout[offset:offset + size]
            if len(blob) != size or output.stdout[offset + size:offset + size + 1] != b'\n':
                raise ValueError('Truncated committed source blob batch')
            blobs[path] = blob
            offset += size + 1
        if offset != len(output.stdout):
            raise ValueError('Unexpected committed source blob output')
    return blobs


def verify_distribution():
    pin = load_json(PIN)
    if JAR.is_symlink() or not JAR.is_file() or not os.access(JAR, os.R_OK):
        raise ValueError('Bundled Checkstyle JAR missing or unreadable')
    checksum = hashlib.sha256(JAR.read_bytes()).hexdigest()
    if not isinstance(pin['sha256'], str) or checksum != pin['sha256']:
        raise ValueError('Bundled Checkstyle checksum is not recorded or does not match')
    with zipfile.ZipFile(JAR) as archive:
        if archive.testzip() is not None:
            raise ValueError('Corrupt bundled Checkstyle archive')
        manifest = archive.read('META-INF/MANIFEST.MF').decode('utf-8')
        if not re.search(r'^Main-Class: com\.puppycrawl\.tools\.checkstyle\.Main\s*$', manifest, re.M):
            raise ValueError('Not an executable Checkstyle distribution')
        for name in ('com/puppycrawl/tools/checkstyle/Main.class',
                     'com/puppycrawl/tools/checkstyle/checks/imports/UnnecessaryFullyQualifiedTypeCheck.class',
                     'picocli/CommandLine.class', 'org/antlr/v4/runtime/Parser.class'):
            if name not in archive.namelist():
                raise ValueError('Checkstyle all-in-one distribution required')
    version = run(['java', '-jar', str(JAR), '--version'], cwd=str(HERE))
    if version.returncode or version.stdout.decode().strip() != 'Checkstyle version: ' + pin['version']:
        raise ValueError('Pinned Checkstyle distribution cannot execute or has the wrong version')
    return pin['version'], checksum


def analyze(repo, source, target, workdir, executor=run, verifier=verify_distribution,
            generated_paths=()):
    started = time.monotonic()
    result = {'version': 1, 'analyzer': 'Checkstyle', 'analyzer_version': None,
              'target': {'repository': str(repo), 'change': f'{target}...{source}'},
              'scope': None, 'files': [], 'diagnostics': [], 'findings': [],
              'evaluations': [], 'limitations': [], 'elapsed_seconds': 0}
    problems = {rule: [] for rule in RULES}
    relevant = {rule: [] for rule in RULES}
    try:
        scope, changed = changes(repo, source, target)
        result['scope'] = scope
        result['target']['change'] = scope['comparison']
        items = [f for f in changed if f['file'].endswith('.java') and f['status'] != 'D']
        # Renames with no edits and deletions have no introduced code.
        items = [f for f in items if f['ranges'] or f['binary']]
        result['files'] = items
        for item in items:
            item['generated'] = generated(item['file']) or any(
                item['file'] == prefix or item['file'].startswith(prefix.rstrip('/') + '/')
                for prefix in generated_paths)
            relevant[RULES[0]].append(item)
            if not item['generated']:
                relevant[RULES[1]].append(item)
        if items:
            version, checksum = verifier()
            result.update(analyzer_version=version, jar_sha256=checksum)
            paths = {}
            blobs = committed_blobs(repo, scope['source'], items)
            for index, item in enumerate(items):
                path = item['file']
                # Export immutable commit blobs, never analyze dirty/staged worktree data.
                blob = blobs[path]
                if blob is None:
                    for rule in RULES:
                        if item in relevant[rule]:
                            problems[rule].append('Non-regular or binary Java source: ' + path)
                    continue
                blob.decode('utf-8')  # Do not silently replace malformed source.
                destination = Path(workdir) / str(index) / PurePosixPath(path).name
                destination.parent.mkdir(parents=True)
                destination.write_bytes(blob)
                paths[str(destination.resolve())] = item
            if paths:
                output = executor(['java', '-jar', str(JAR),
                                   '-c', str(CONFIG), '-f', 'xml', *paths], cwd=str(workdir))
                parse_output(output, paths, result, problems)
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, KeyError,
            subprocess.SubprocessError, ET.ParseError) as exc:
        # Never echo raw analyzer/Git output or source that might contain secrets.
        message = str(exc) if isinstance(exc, ValueError) and not isinstance(exc, UnicodeError) else type(exc).__name__
        result['limitations'].append(message)
        result['findings'] = []
        for diagnostic in result['diagnostics']:
            if diagnostic['analysis_status'] == 'CONFIRMED':
                diagnostic['analysis_status'] = 'REQUIRES_VERIFICATION'
        for rule in RULES:
            if relevant[rule] or result['scope'] is None:
                problems[rule].append('Analysis incomplete: ' + message)
    for rule in RULES:
        matches = [f for f in result['findings'] if f['id'].startswith('SA-' + rule + '-')]
        incomplete = problems[rule]
        applicable = relevant[rule]
        status = ('UNVERIFIED' if incomplete else 'FAIL' if matches else
                  'PASS' if applicable else 'NOT_APPLICABLE')
        locations = [{'file': item['file'], 'start_line': a, 'end_line': b}
                     for item in applicable for a, b in item['ranges']]
        if status == 'FAIL':
            locations = [loc for finding in matches for loc in finding['locations']]
        reason = {'PASS': 'Checkstyle completed for all relevant changed lines within the documented check domain.',
                  'FAIL': 'Confirmed introduced violations from Checkstyle.',
                  'UNVERIFIED': 'Deterministic analysis or attribution is incomplete.',
                  'NOT_APPLICABLE': 'No relevant added/modified Java lines (deleted and rename-only files excluded).'}[status]
        result['evaluations'].append({'rule_id': rule, 'status': status, 'reason': reason,
            'inspected': locations, 'evidence': ['static-analysis-results.json: ' + reason] if applicable or matches else [],
            'finding_ids': [f['id'] for f in matches] if status == 'FAIL' else [],
            'limitations': sorted(set(incomplete)),
            'needed': ['Resolve analyzer/attribution limitations or perform targeted verification of uncovered contexts.'] if incomplete else []})
    result['analysis_status'] = 'UNVERIFIED' if any(problems.values()) else 'COMPLETE'
    result['elapsed_seconds'] = round(time.monotonic() - started, 6)
    return result


def parse_output(output, paths, result, problems):
    root = ET.fromstring(output.stdout)
    if root.tag != 'checkstyle' or root.attrib.get('version') != result['analyzer_version']:
        raise ValueError('Invalid Checkstyle XML identity')
    seen = set()
    count = 0
    for node in root:
        if node.tag != 'file' or node.get('name') not in paths or node.get('name') in seen:
            raise ValueError('Incomplete or unexpected Checkstyle file attribution')
        seen.add(node.get('name'))
        item = paths[node.get('name')]
        fqcn_gap = any(e.get('source') == LIMIT_SOURCE or e.get('source') not in SOURCES
                       for e in node)
        for error in node:
            count += 1
            source = error.get('source', '')
            rule = SOURCES.get(source)
            if source == LIMIT_SOURCE:
                if not item['generated']:
                    problems[RULES[1]].append('Known FQCN check coverage gap in ' + item['file'])
                continue
            if not rule:
                for affected in RULES:
                    if affected == RULES[0] or not item['generated']:
                        problems[affected].append('Parser/analyzer error in ' + item['file'])
                continue
            if rule == RULES[1] and item['generated']:
                continue
            line, column = int(error.get('line', '0')), int(error.get('column', '0'))
            if line < 1 or column < 1:
                problems[rule].append('Missing diagnostic location in ' + item['file'])
                continue
            introduced = any(a <= line <= b for a, b in item['ranges'])
            # Do not include source snippets or arbitrary tool messages in artifacts.
            message = ('Static import prohibited by team convention.' if rule == RULES[0] else
                       'Unnecessary fully qualified Java type; use an import and simple name.')
            diagnostic = {'rule_id': rule, 'analyzer': 'Checkstyle',
                'analyzer_version': result['analyzer_version'], 'file': item['file'],
                'line': line, 'column': column, 'severity': 'P3', 'message': message,
                'evidence': [source, 'Committed source analyzed; location compared with added-line ranges.'],
                'analysis_status': 'CONFIRMED' if introduced else 'OUTSIDE_CHANGED_LINES'}
            if rule == RULES[1] and fqcn_gap:
                diagnostic['analysis_status'] = 'REQUIRES_VERIFICATION'
            result['diagnostics'].append(diagnostic)
            if diagnostic['analysis_status'] == 'REQUIRES_VERIFICATION':
                continue
            if not introduced:
                # May be legacy or affected indirectly (e.g. removed conflicting import).
                # Do not turn it into a finding without targeted attribution.
                if rule == RULES[1]:
                    problems[rule].append('Unchanged-line FQCN diagnostic requires attribution: ' + item['file'])
                continue
            finding_id = 'SA-' + rule + '-' + hashlib.sha256(
                f'{item["file"]}:{line}:{column}'.encode()).hexdigest()[:12]
            result['findings'].append({'id': finding_id, 'priority': 'P3', 'title': message,
                'locations': [{'file': item['file'], 'start_line': line, 'end_line': line}],
                'evidence': diagnostic['evidence'] + [f'Checkstyle {result["analyzer_version"]}; column {column}']})
    if seen != set(paths):
        raise ValueError('Checkstyle did not report every submitted file')
    # POSIX process exit status retains only the low eight bits.
    expected_exit = count % 256 if os.name == 'posix' else count
    if output.returncode != expected_exit:
        raise ValueError('Checkstyle execution failed or XML result is incomplete')


def merge_coverage(report, result):
    """Reuse the existing finding/evaluation contract; preserve unrelated declarations."""
    from validators.validate_coverage import summary
    if report['target'] != result['target']:
        raise ValueError('Coverage scope/repository does not match static analysis')
    ids = {e['rule_id'] for e in result['evaluations']}
    old_ids = {f['id'] for f in report['findings']}
    if any(f['id'] in old_ids for f in result['findings']):
        raise ValueError('Static finding ID collision; reconcile explicitly')
    report['evaluations'] = [e for e in report['evaluations'] if e['rule_id'] not in ids] + result['evaluations']
    report['findings'] += result['findings']
    report['summary'] = summary(report['evaluations'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--review-id', required=True)
    parser.add_argument('--coverage-draft', type=Path)
    parser.add_argument('--generated-path', action='append', default=[],
                        help='Known generated file/directory relative to repository; repeatable, FQCN only')
    args = parser.parse_args()
    try:
        if any(PurePosixPath(p).is_absolute() or '..' in PurePosixPath(p).parts or
               p in ('', '.', '/') for p in args.generated_path):
            raise ValueError('Generated paths must be explicit repository-relative files/directories')
        repo, state = external_state()
        if (state / 'static-analysis-results.json').exists() or (state / 'static-analysis-results.json').is_symlink():
            raise ValueError('Static analysis already has an artifact; use a new review state')
        from _integrity import baseline, verify_state
        verify_state(repo, baseline(state), 'before-static-analysis')
        # Establish audit identity before executing; rejects mixed review IDs.
        append_event(args.review_id, 'static_analysis_started', 'static_analyzer', list(RULES), {})
        try:
            with tempfile.TemporaryDirectory(prefix='checkstyle-', dir=state) as workdir:
                result = analyze(repo, args.source, args.target, workdir,
                                 generated_paths=args.generated_path)
        finally:
            verify_state(repo, baseline(state), 'after-static-analysis')
        result['review_id'] = args.review_id
        print(write_artifact('static-analysis-results.json', result))
        append_event(args.review_id, 'static_analysis_result', 'static_analyzer', list(RULES),
                     {'analysis_status': result['analysis_status'], 'elapsed_seconds': result['elapsed_seconds'],
                      'statuses': {e['rule_id']: e['status'] for e in result['evaluations']}})
        if args.coverage_draft:
            report = load_json(args.coverage_draft)
            if report['review_id'] != args.review_id:
                raise ValueError('Coverage review ID mismatch')
            report = merge_coverage(report, result)
            from validators.rule_registry import registry
            from validators.validate_coverage import validate_report
            if validate_report(report, registry())['classification'] == 'INVALID':
                raise ValueError('Merged coverage is invalid')
            print(write_artifact('rule-coverage-static-draft.json', report))
        return 3 if result['analysis_status'] == 'UNVERIFIED' else 0
    except HookError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError) as exc:
        print('Static analysis unavailable: ' + type(exc).__name__, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
