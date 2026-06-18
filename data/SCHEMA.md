# IDAC YAML Schema

Each file in `data/idacs/<slug>.yaml` describes a single Independent Data
Access Center. The public dashboard is built directly from these files —
edit one, open a pull request, and once it merges the site rebuilds.

## Top-level fields

| Field                    | Type    | Required | Description |
|--------------------------|---------|----------|-------------|
| `country`                | string  | yes      | Display name of the host country. |
| `slug`                   | string  | yes      | URL-safe identifier; must match the file name. |
| `location`               | object  | yes      | Map pin and host institution (see below). |
| `data_products`          | object  | yes      | Booleans for each Rubin data product (see below). |
| `data_releases`          | list    | yes      | Planned Rubin data releases hosted, e.g. `["DP1", "DR1"]`. May be empty. |
| `capacity`               | object  | yes      | Numerical compute & storage commitments. |
| `hardware`               | object  | yes      | Free-text descriptions of the hardware (may be empty strings). |
| `software_services`      | string  | yes      | Description of the user-facing platform / batch system / databases. |
| `complementary_datasets` | string  | yes      | Non-Rubin datasets co-located at this IDAC. |
| `use_cases`              | string  | yes      | Science the site specializes in supporting. |
| `science_collaboration_agreements` | string | yes | Rubin Science Collaboration agreements this IDAC has in place (free text — list collaborations, status, etc.). Empty string allowed. |
| `documentation`          | list    | yes      | Onboarding / portal links (objects with `title`, `url`). |
| `contacts`               | list    | yes      | Objects with `name`, `email`, `role`. |
| `notes`                  | string  | yes      | Free-form caveats. May be empty. |

## `location`

```yaml
location:
  city: "Edinburgh"
  institution: "Royal Observatory / UK Data Facility"
  lat: 55.923
  lng: -3.187
```

## `data_products`

All twelve booleans below must be present. `true` means the IDAC plans to
host that product type.

```yaml
data_products:
  object_table_subset:  true
  object_table:         true
  source_table:         true
  forced_source_table:  true
  dia_object_table:     true
  dia_source_table:     true
  solar_system_tables:  true
  co_added_images:      true
  visit_images:         true
  difference_images:    false
  template_images:      true
  other_data_products:  true
```

## `capacity`

Integrated capacity over the 13-year IDAC lifetime. Use `null` if a value
is genuinely unknown. The "free" fields are the excess after deducting the
contributing community's reserved share.

```yaml
capacity:
  storage_pb_years:      2005      # total storage commitment (PB-years)
  free_storage_pb_years: 10.9      # excess available for non-local users
  cpu_mhrs:              61        # total CPU (millions of core-hours)
  free_cpu_mhrs:         41.1
  gpu_mhrs:              null      # GPU (millions of GPU-hours), null if N/A
  free_gpu_mhrs:         null
  hosted_data_pb_years:  1989      # data hosted (PB-years)
  expected_local_users:  437       # PI-funded local user community
```

## `hardware`

Free-text descriptions so users can tell whether the hardware suits their
workload. Empty strings are fine, but encouraged to fill in.

```yaml
hardware:
  cpu_architecture: "AMD EPYC 9654 (Genoa), 384 cores/node"
  gpu_architecture: "NVIDIA H100 80GB SXM5"
  storage_type:     "CephFS object store + Lustre scratch"
  network:          "InfiniBand HDR 200 Gb/s"
```

## `documentation`

```yaml
documentation:
  - title: "UK IDAC onboarding guide"
    url:   "https://example.org/uk-idac/onboarding"
  - title: "Science platform login"
    url:   "https://rsp.example.org"
```

## `contacts`

```yaml
contacts:
  - name:  "Jane Doe"
    email: "jane@example.org"
    role:  "Technical lead"
```

## Editing checklist for IDAC representatives

1. Find your file: `data/idacs/<your-country>.yaml`.
2. Edit any field. Multi-line strings use YAML's `|` literal-block syntax —
   indent each line two spaces.
3. Validate locally (optional): `python3 scripts/build.py` — it will refuse
   to build if a required field is missing.
4. Open a pull request. The site rebuilds automatically on merge.
