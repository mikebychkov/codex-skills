"""JSONL provenance events. Local records are not tamper-proof attestations."""
import json
import os
from datetime import datetime, timezone
from validators.common import external_state

SOURCES = {
    "static_analysis_started": "static_analyzer",
    "static_analysis_result": "static_analyzer",
    "rules_registered": "registry",
    "rule_files_supplied": "registry",
    "tool_read_confirmed": "harness_observed",
    "reviewer_evaluation": "reviewer_declared",
    "validator_result": "validator",
    "judge_result": "judge_assessment",
}


def append_event(review_id, event_type, source, rule_ids, details, *, event_reference=None):
    if not isinstance(review_id, str) or not review_id.strip():
        raise ValueError("Nonempty review ID required")
    if SOURCES.get(event_type) != source:
        raise ValueError("Invalid audit event type/source")
    if event_type in ("tool_read_confirmed", "judge_result") and not event_reference:
        raise ValueError("Actual harness/tool or judge execution reference required")
    if not isinstance(rule_ids, list) or any(not isinstance(i, str) for i in rule_ids):
        raise ValueError("rule_ids must be a list of strings")
    _, state = external_state()
    identity_path = state / "coverage-identity.json"
    identity = {"review_id": review_id}
    try:
        with identity_path.open("x", encoding="utf-8") as stream:
            json.dump(identity, stream)
    except FileExistsError:
        from validators.common import load_json
        if identity_path.is_symlink() or load_json(identity_path) != identity:
            raise ValueError("Audit review ID differs from external state identity")
    event = {"timestamp": datetime.now(timezone.utc).isoformat(), "review_id": review_id,
             "event_type": event_type, "source": source, "rule_ids": rule_ids,
             "details": details}
    if event_reference:
        event["event_reference"] = event_reference
    data = (json.dumps(event, sort_keys=True, allow_nan=False) + "\n").encode()
    # O_NOFOLLOW blocks an audit-file symlink; append-only at application level.
    fd = os.open(state / "rule-coverage-audit.jsonl",
                 os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    try:
        if os.write(fd, data) != len(data):
            raise OSError("Incomplete audit event write")
    finally:
        os.close(fd)
    return event
