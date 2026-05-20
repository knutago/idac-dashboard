#!/usr/bin/env python3
"""
One-time migration: pull the IDAC Capabilities spreadsheet and emit one YAML
file per IDAC into data/idacs/.

After the initial seed, IDAC representatives edit the YAML files directly --
this script is preserved only for reproducibility / re-seeding from scratch.

Re-running this script will OVERWRITE any human edits. Don't.

Usage:
    python3 scripts/seed.py
"""
from __future__ import annotations

import csv
import io
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "idacs"

SHEET_ID = "1r6JH0_5ROdSZ7I9_N4eSEHGbYgOO2QOwW_70IGo8RSg"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# Representative location for each IDAC's primary host institution.
LOCATIONS = {
    "United Kingdom":  {"city": "Edinburgh",     "institution": "Royal Observatory / UK Data Facility", "lat": 55.923,  "lng":  -3.187},
    "Australia":       {"city": "Perth",         "institution": "Pawsey Supercomputing Centre",          "lat": -31.978, "lng": 115.819},
    "Brazil":          {"city": "Rio de Janeiro","institution": "LIneA",                                 "lat": -22.953, "lng": -43.176},
    "Canada":          {"city": "Victoria",      "institution": "Canadian Astronomy Data Centre (NRC Herzberg)", "lat": 48.519, "lng": -123.418},
    "Croatia":         {"city": "Zagreb",        "institution": "Ruđer Bošković Institute / SRCE",       "lat": 45.825,  "lng":  15.978},
    "Denmark":         {"city": "Copenhagen",    "institution": "DARK / Niels Bohr Institute",           "lat": 55.696,  "lng":  12.570},
    "Japan":           {"city": "Mitaka",        "institution": "National Astronomical Observatory of Japan (NAOJ)", "lat": 35.675, "lng": 139.541},
    "Mexico":          {"city": "Puebla",        "institution": "INAOE",                                 "lat": 19.022,  "lng": -98.313},
    "Poland":          {"city": "Poznań",        "institution": "Poznań Supercomputing and Networking Center", "lat": 52.406, "lng": 16.925},
    "Slovenia":        {"city": "Ljubljana",     "institution": "University of Ljubljana",               "lat": 46.043,  "lng":  14.488},
    "Spain":           {"city": "Barcelona",     "institution": "Port d'Informació Científica (PIC) / IFAE", "lat": 41.500, "lng": 2.111},
    "South Korea":     {"city": "Daejeon",       "institution": "Korea Astronomy and Space Science Institute (KASI)", "lat": 36.398, "lng": 127.388},
    "Argentina":       {"city": "La Plata",      "institution": "Facultad de Ciencias Astronómicas (UNLP)", "lat": -34.908, "lng": -57.953},
}

PRODUCT_KEYS = [
    "object_table_subset",
    "object_table",
    "source_table",
    "forced_source_table",
    "dia_object_table",
    "dia_source_table",
    "solar_system_tables",
    "co_added_images",
    "visit_images",
    "difference_images",
    "template_images",
    "other_data_products",
]

COL = {
    "country": 0,
    "products_start": 1,
    "product_comments": 13,
    "software": 14,
    "use_cases": 15,
    "contacts": 16,
    "storage": 17,
    "cpu": 18,
    "gpu": 19,
    "hosted": 20,
    "users": 21,
    "free_storage": 22,
    "free_cpu": 23,
    "free_gpu": 24,
    "notes": 25,
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def parse_number(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() == "tbd":
        return None
    try:
        n = float(s.replace(",", ""))
        return int(n) if n.is_integer() else round(n, 3)
    except ValueError:
        return None


def parse_bool(v) -> bool:
    return str(v).strip().upper() == "TRUE"


def parse_contacts(text: str) -> list[dict]:
    """Best-effort extraction of name/email/role tuples from free-form contact text."""
    contacts: list[dict] = []
    if not text:
        return contacts
    current_role = ""
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().rstrip(":").endswith("contact") or line.lower().rstrip(":").endswith("contacts"):
            current_role = line.rstrip(":").strip()
            continue
        # A single line can hold multiple "Name - email" pairs separated by ';' or ','.
        # Split only when each chunk still contains an email.
        if line.count("@") > 1:
            chunks = [c.strip() for c in re.split(r"[;]", line) if c.strip()]
        else:
            chunks = [line]
        for chunk in chunks:
            m = EMAIL_RE.search(chunk)
            if m:
                email = m.group(0).rstrip(".,;:")
                name = (chunk[: m.start()] + chunk[m.end():]).strip(" -()<>,;\t")
                contacts.append({
                    "name": name or "(name not listed)",
                    "email": email,
                    "role": current_role,
                })
            else:
                contacts.append({"name": chunk, "email": "", "role": current_role})
    return contacts


# --- YAML emission --------------------------------------------------------

def yaml_quote(v) -> str:
    """Render a scalar value safely for YAML."""
    if v is None or v == "":
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    # Always double-quote strings for predictability; escape \ and ".
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def literal_block_lines(text: str, indent: int = 2) -> list[str]:
    """Emit a `|`-style literal block. Returns lines including the `|` header."""
    if not text:
        # An empty quoted string is the inline form -- no header needed.
        return ['""']
    pad = " " * indent
    out = ["|"]
    for line in text.splitlines():
        out.append(pad + line if line else "")
    return out


def render_yaml(record: dict) -> str:
    """Render the record as a hand-readable YAML file. No textwrap, just direct lines."""
    country = record["country"]
    loc = record["location"]
    products = record["products"]
    cap = record["capacity"]
    contacts = record["contacts"]

    L: list[str] = []
    add = L.append

    add("# " + "=" * 76)
    add(f"# Rubin IDAC Capabilities -- {country}")
    add("# " + "-" * 76)
    add("# This file is the source of truth for what the public IDAC dashboard shows")
    add(f"# about the {country} IDAC. Open a pull request with any change you want")
    add("# published. See data/SCHEMA.md for field definitions.")
    add("# " + "=" * 76)
    add("")
    add(f"country: {yaml_quote(country)}")
    add(f"slug: {yaml_quote(record['slug'])}")
    add("")
    add("location:")
    add(f"  city:        {yaml_quote(loc['city'])}")
    add(f"  institution: {yaml_quote(loc['institution'])}")
    add(f"  lat: {loc['lat']}")
    add(f"  lng: {loc['lng']}")
    add("")
    add("# === Rubin data products that will be hosted at this IDAC =================")
    add("data_products:")
    add(f"  object_table_subset:  {yaml_quote(products['object_table_subset'])}")
    add(f"  object_table:         {yaml_quote(products['object_table'])}")
    add(f"  source_table:         {yaml_quote(products['source_table'])}")
    add(f"  forced_source_table:  {yaml_quote(products['forced_source_table'])}")
    add(f"  dia_object_table:     {yaml_quote(products['dia_object_table'])}")
    add(f"  dia_source_table:     {yaml_quote(products['dia_source_table'])}")
    add(f"  solar_system_tables:  {yaml_quote(products['solar_system_tables'])}")
    add(f"  co_added_images:      {yaml_quote(products['co_added_images'])}")
    add(f"  visit_images:         {yaml_quote(products['visit_images'])}")
    add(f"  difference_images:    {yaml_quote(products['difference_images'])}")
    add(f"  template_images:      {yaml_quote(products['template_images'])}")
    add(f"  other_data_products:  {yaml_quote(products['other_data_products'])}")
    add("")
    add("# === Rubin data releases stored at this IDAC ==============================")
    add('# List the planned data releases, e.g. ["DP1", "DR1", "DR2"]. Leave [] if TBD.')
    add("data_releases: []")
    add("")
    add("# === Capacity (integrated over the 13-year IDAC lifetime) =================")
    add("capacity:")
    add(f"  storage_pb_years:      {yaml_quote(cap['storage'])}")
    add(f"  free_storage_pb_years: {yaml_quote(cap['free_storage'])}")
    add(f"  cpu_mhrs:              {yaml_quote(cap['cpu'])}")
    add(f"  free_cpu_mhrs:         {yaml_quote(cap['free_cpu'])}")
    add(f"  gpu_mhrs:              {yaml_quote(cap['gpu'])}")
    add(f"  free_gpu_mhrs:         {yaml_quote(cap['free_gpu'])}")
    add(f"  hosted_data_pb_years:  {yaml_quote(cap['hosted'])}")
    add(f"  expected_local_users:  {yaml_quote(cap['users'])}")
    add("")
    add("# === Hardware architecture (FREE-TEXT, please fill in) ====================")
    add('# e.g. "AMD EPYC 9654 (Genoa), 384 cores/node" / "NVIDIA H100 80GB SXM5"')
    add("hardware:")
    add('  cpu_architecture: ""')
    add('  gpu_architecture: ""')
    add('  storage_type:     ""')
    add('  network:          ""')
    add("")
    add("# === Software services & platform =========================================")
    block = literal_block_lines(record["software"])
    add(f"software_services: {block[0]}")
    for line in block[1:]:
        add(line)
    add("")
    add("# === Complementary / auxiliary datasets ===================================")
    block = literal_block_lines(record["product_comments"])
    add(f"complementary_datasets: {block[0]}")
    for line in block[1:]:
        add(line)
    add("")
    add("# === Science use cases this IDAC specializes in ===========================")
    block = literal_block_lines(record["use_cases"])
    add(f"use_cases: {block[0]}")
    for line in block[1:]:
        add(line)
    add("")
    add("# === Onboarding & documentation links (please fill in) ====================")
    add("documentation:")
    add('  - title: "Onboarding guide"')
    add('    url:   ""')
    add('  - title: "Science platform / user portal"')
    add('    url:   ""')
    add("")
    add("# === Contacts =============================================================")
    add("contacts:")
    if not contacts:
        add("  []  # TODO: add at least one contact")
    else:
        for c in contacts:
            add(f"  - name:  {yaml_quote(c['name'])}")
            add(f"    email: {yaml_quote(c['email'])}")
            add(f"    role:  {yaml_quote(c['role'])}")
    add("")
    add("# === Free-text notes ======================================================")
    block = literal_block_lines(record["notes"])
    add(f"notes: {block[0]}")
    for line in block[1:]:
        add(line)
    add("")

    return "\n".join(L)


def fetch_rows() -> list[list[str]]:
    print(f"Fetching {CSV_URL}")
    with urllib.request.urlopen(CSV_URL) as resp:
        text = resp.read().decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    return list(reader)


def main() -> int:
    rows = fetch_rows()
    header_idx = next(
        i for i, r in enumerate(rows)
        if r and r[0].strip() == "Host country"
    )
    data_start = header_idx + 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0

    for row in rows[data_start:]:
        if not row or not row[COL["country"]].strip():
            continue
        country = row[COL["country"]].strip()
        if country not in LOCATIONS:
            print(f"  ! No location mapping for {country!r} -- skipping.")
            continue

        products = {
            key: parse_bool(row[COL["products_start"] + i])
            for i, key in enumerate(PRODUCT_KEYS)
        }
        record = {
            "country": country,
            "slug": slugify(country),
            "location": LOCATIONS[country],
            "products": products,
            "capacity": {
                "storage":      parse_number(row[COL["storage"]]),
                "cpu":          parse_number(row[COL["cpu"]]),
                "gpu":          parse_number(row[COL["gpu"]]),
                "hosted":       parse_number(row[COL["hosted"]]),
                "users":        parse_number(row[COL["users"]]),
                "free_storage": parse_number(row[COL["free_storage"]]),
                "free_cpu":     parse_number(row[COL["free_cpu"]]),
                "free_gpu":     parse_number(row[COL["free_gpu"]]),
            },
            "software":         row[COL["software"]].strip(),
            "product_comments": row[COL["product_comments"]].strip(),
            "use_cases":        row[COL["use_cases"]].strip(),
            "contacts":         parse_contacts(row[COL["contacts"]]),
            "notes":            row[COL["notes"]].strip(),
        }

        out_path = OUT_DIR / f"{record['slug']}.yaml"
        out_path.write_text(render_yaml(record), encoding="utf-8")
        print(f"  + wrote {out_path.relative_to(ROOT)}")
        written += 1

    print(f"\nSeeded {written} IDAC files into {OUT_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
