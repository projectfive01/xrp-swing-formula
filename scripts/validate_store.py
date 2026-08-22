#!/usr/bin/env python3
"""Validate XRP research store JSONL + variants against schemas/ rules.

Uses jsonschema if installed; otherwise runs a built-in required-field + type check
aligned to the same contracts so CI works with stdlib only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "data").is_dir():
    DATA = ROOT / "data"
else:
    DATA = ROOT
SCHEMAS = ROOT / "schemas"

JSONL_MAP = {
    "trades.jsonl": "trade.schema.json",
    "gate_scans.jsonl": "gate_scan.schema.json",
    "signals.jsonl": "signal.schema.json",
    "findings.jsonl": "finding.schema.json",
    "market_snapshots.jsonl": "market_snapshot.schema.json",
    "analytics_runs.jsonl": "analytics_run.schema.json",
}

BASE_FREEZE = {
    "code": "BASE",
    "ret_thresh": 0.20,
    "lookback": 10,
    "rsi_thresh": 75,
    "pb_thresh": 0.10,
    "hold_days": 10,
}


def load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text())


def validate_with_jsonschema(instance, schema) -> list[str]:
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
        v = Draft202012Validator(schema)
        return [f"{e.message} @ {list(e.path)}" for e in v.iter_errors(instance)]
    except ImportError:
        return validate_builtin(instance, schema)


def validate_builtin(instance, schema) -> list[str]:
    errs = []
    if schema.get("type") == "object" and not isinstance(instance, dict):
        return [f"expected object, got {type(instance).__name__}"]
    for key in schema.get("required", []):
        if key not in instance:
            errs.append(f"missing required property: {key}")
    props = schema.get("properties", {})
    for key, val in instance.items():
        if key not in props:
            continue
        p = props[key]
        types = p.get("type")
        if types is None:
            continue
        if not isinstance(types, list):
            types = [types]
        ok = False
        for t in types:
            if t == "null" and val is None:
                ok = True
            elif t == "string" and isinstance(val, str):
                ok = True
            elif t == "number" and isinstance(val, (int, float)) and not isinstance(val, bool):
                ok = True
            elif t == "integer" and isinstance(val, int) and not isinstance(val, bool):
                ok = True
            elif t == "boolean" and isinstance(val, bool):
                ok = True
            elif t == "array" and isinstance(val, list):
                ok = True
            elif t == "object" and isinstance(val, dict):
                ok = True
        if val is not None and not ok and "null" not in types:
            errs.append(f"{key}: expected {types}, got {type(val).__name__}")
        if "enum" in p and val is not None and val not in p["enum"]:
            errs.append(f"{key}: {val!r} not in enum {p['enum']}")
    return errs


def validate_jsonl(path: Path, schema_name: str) -> list[str]:
    schema = load_schema(schema_name)
    errors = []
    if not path.exists():
        return [f"missing file: {path}"]
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}:{i}: invalid JSON ({e})")
            continue
        for err in validate_with_jsonschema(obj, schema):
            errors.append(f"{path.name}:{i}: {err}")
    return errors


def validate_variants() -> list[str]:
    path = DATA / "variants.json"
    schema = load_schema("variants.schema.json")
    if not path.exists():
        return [f"missing {path}"]
    obj = json.loads(path.read_text())
    errors = validate_with_jsonschema(obj, schema)
    variants = obj.get("variants", [])
    base = next((v for v in variants if v.get("code") == "BASE"), None)
    if base is None:
        errors.append("BASE variant missing")
    else:
        for k, expected in BASE_FREEZE.items():
            if k == "code":
                continue
            if base.get(k) != expected:
                errors.append(f"BASE freeze violated: {k}={base.get(k)!r} expected {expected!r}")
    return [f"variants.json: {e}" for e in errors]


def main() -> int:
    all_errors = []
    for fname, schema_name in JSONL_MAP.items():
        all_errors.extend(validate_jsonl(DATA / fname, schema_name))
    all_errors.extend(validate_variants())
    if all_errors:
        print("VALIDATION FAILED")
        for e in all_errors:
            print(" -", e)
        return 1
    print("VALIDATION OK")
    print(f"  schemas: {len(list(SCHEMAS.glob('*.json')))}")
    print(f"  checked: {', '.join(JSONL_MAP)} + variants.json")
    print("  BASE freeze: intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
