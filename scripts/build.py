#!/usr/bin/env python3
"""
Build step: read every data/idacs/*.yaml and emit a single idacs.json that
the dashboard fetches at runtime.

Validates the required top-level fields are present in each file and aborts
on the first malformed file so CI fails loudly.

Usage:
    python3 scripts/build.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "idacs"
OUTPUT = ROOT / "idacs.json"

REQUIRED_TOP_LEVEL = {
    "country", "slug", "location", "data_products", "data_releases",
    "capacity", "hardware", "software_services", "complementary_datasets",
    "use_cases", "science_collaboration_agreements",
    "documentation", "contacts", "notes",
}
REQUIRED_LOCATION = {"city", "institution", "lat", "lng"}
REQUIRED_PRODUCTS = {
    "object_table_subset", "object_table", "source_table", "forced_source_table",
    "dia_object_table", "dia_source_table", "solar_system_tables",
    "co_added_images", "visit_images", "difference_images", "template_images",
    "other_data_products",
}
REQUIRED_CAPACITY = {
    "storage_pb_years", "free_storage_pb_years", "cpu_mhrs", "free_cpu_mhrs",
    "gpu_mhrs", "free_gpu_mhrs", "hosted_data_pb_years", "expected_local_users",
}
REQUIRED_HARDWARE = {"cpu_architecture", "gpu_architecture", "storage_type", "network"}


def fail(path: Path, msg: str) -> None:
    sys.stderr.write(f"ERROR in {path.relative_to(ROOT)}: {msg}\n")
    sys.exit(1)


def validate(path: Path, data: dict) -> None:
    if not isinstance(data, dict):
        fail(path, "top-level YAML must be a mapping")
    missing = REQUIRED_TOP_LEVEL - set(data)
    if missing:
        fail(path, f"missing required fields: {sorted(missing)}")
    for sub_name, required in (
        ("location", REQUIRED_LOCATION),
        ("data_products", REQUIRED_PRODUCTS),
        ("capacity", REQUIRED_CAPACITY),
        ("hardware", REQUIRED_HARDWARE),
    ):
        sub = data.get(sub_name) or {}
        if not isinstance(sub, dict):
            fail(path, f"`{sub_name}` must be a mapping")
        sub_missing = required - set(sub)
        if sub_missing:
            fail(path, f"`{sub_name}` missing keys: {sorted(sub_missing)}")
    if not isinstance(data.get("contacts"), list):
        fail(path, "`contacts` must be a list (may be empty)")
    if not isinstance(data.get("documentation"), list):
        fail(path, "`documentation` must be a list (may be empty)")
    if not isinstance(data.get("data_releases"), list):
        fail(path, "`data_releases` must be a list (may be empty)")
    if data["slug"] != path.stem:
        fail(path, f"slug {data['slug']!r} must match file name {path.stem!r}")


def main() -> int:
    if not DATA_DIR.is_dir():
        sys.exit(f"Data directory not found: {DATA_DIR}")

    records = []
    for path in sorted(DATA_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            fail(path, f"YAML parse error: {e}")
        if data is None:
            fail(path, "file is empty")
        validate(path, data)
        # Tag with source-file path so the dashboard can render an "Edit on
        # GitHub" link straight to this file.
        data["_source_file"] = f"data/idacs/{path.name}"
        records.append(data)

    records.sort(key=lambda r: r["country"])

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "idacs": records,
    }

    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(records)} IDACs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
