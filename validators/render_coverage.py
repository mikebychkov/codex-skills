"""Render the coverage section only; the surrounding review contract still applies."""

def render(report, result):
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    totals = report['summary']
    lines = ['### Rule Coverage Report', '',
             ', '.join(f'{key}: {totals[key]}' for key in
                       ('registered', 'applicable', 'passed', 'failed', 'not_applicable', 'unverified')),
             '', f'Coverage completion status: {result["classification"]}.',
             'Statuses are reviewer declarations; structural validity is not semantic verification.',
             f'Ruleset SHA-256: `{report["ruleset"]["sha256"]}`.', '',
             '| Rule ID | Status | Evidence / Reason |', '|---|---|---|']
    for entry in report['evaluations']:
        details = [entry['reason'], *entry['evidence'], *entry['limitations'], *entry['needed']]
        details += [loc['file'] + (f':{loc["start_line"]}-{loc["end_line"]}' if 'start_line' in loc else '')
                    for loc in entry['inspected']]
        details += entry['finding_ids']
        lines.append(f'| {cell(entry["rule_id"])} | {entry["status"]} | {cell("; ".join(details))} |')
    lines += ['', 'Read confirmation and judge execution must be established from actual audit events; '
              'this table does not establish either.']
    return '\n'.join(lines) + '\n'
