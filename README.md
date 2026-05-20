# Rubin IDAC Resources Dashboard

A static, public-facing dashboard showing the compute, storage, and data
products available at each of the Vera C. Rubin Observatory's Independent
Data Access Centers (IDACs).

> Live site: _(to be set up via GitHub Pages — see [Deployment](#deployment))_

---

## How it works

```
data/idacs/<country>.yaml        # source of truth: one file per IDAC
        │
        ▼
scripts/build.py                 # validates + concatenates into a single JSON
        │
        ▼
idacs.json                       # what the dashboard fetches at runtime
        │
        ▼
index.html + assets/app.js       # render the dashboard
```

The dashboard itself is plain HTML / CSS / JS built on top of the
[Tabler](https://tabler.io/) dashboard template. There is no Node build, no
React, no framework runtime — it works as a static page on GitHub Pages.

---

## For IDAC representatives: updating your entry

All published information about your IDAC lives in **one file**:

```
data/idacs/<your-country>.yaml
```

For example, the UK IDAC is at [`data/idacs/united-kingdom.yaml`](data/idacs/united-kingdom.yaml).

To update anything (e.g. fill in hardware architecture, add a documentation
link, refresh contacts, mark new data products as hosted):

1. Open the file directly on GitHub and click the pencil icon, **or**
   clone the repo and edit locally.
2. Change any field. See [`data/SCHEMA.md`](data/SCHEMA.md) for what each
   field means and the allowed types.
3. Commit and open a pull request.
4. Once the PR merges, the [GitHub Pages workflow](.github/workflows/pages.yml)
   rebuilds and redeploys the dashboard automatically.

The dashboard also renders an **"Edit this profile on GitHub"** link at the
bottom of every IDAC profile card, which deep-links to your YAML file in
the default branch.

### Fields that are currently empty and worth filling in

The initial seed from the IDAC Capabilities spreadsheet left these fields
blank — they're the most impactful to populate:

- `hardware.cpu_architecture` / `gpu_architecture` / `storage_type` / `network`
- `data_releases`
- `documentation` URLs (onboarding guide, science platform login, etc.)
- Contact `role` strings if the import lost them

---

## Repository layout

```
.
├── index.html                    # Tabler-based dashboard page
├── idacs.json                    # built artifact, written by scripts/build.py
├── assets/
│   ├── app.js                    # render logic (map / table / matrix / cards)
│   └── app.css                   # local additions on top of Tabler
├── data/
│   ├── SCHEMA.md                 # field-by-field schema reference
│   └── idacs/
│       ├── argentina.yaml
│       ├── australia.yaml
│       ├── brazil.yaml
│       └── … (one file per IDAC)
├── scripts/
│   ├── build.py                  # YAML → idacs.json (with validation)
│   └── seed.py                   # one-off migration from the Google Sheet
└── .github/workflows/pages.yml   # auto-build + deploy on push to main
```

---

## Working on the dashboard locally

### Prerequisites

- Python 3.10+
- `pip install pyyaml`

### Build & preview

```sh
# 1. Regenerate idacs.json from the YAML files
python3 scripts/build.py

# 2. Serve the static site
python3 -m http.server 8123

# 3. Open http://localhost:8123 in a browser
```

The build script validates every YAML file against the required schema and
aborts with a descriptive error on the first malformed file, so CI fails
loudly if a contributor introduces a structural mistake.

---

## Deployment

The dashboard is deployed to GitHub Pages via the workflow in
[`.github/workflows/pages.yml`](.github/workflows/pages.yml). On every push
to `main` it:

1. Installs Python + PyYAML.
2. Runs `python3 scripts/build.py` to produce a fresh `idacs.json`.
3. Uploads the whole site (HTML, CSS, JS, JSON) as a Pages artifact.
4. Deploys to the project's GitHub Pages site.

### One-time setup

1. Push the repo to GitHub.
2. Edit `index.html` and replace the `data-repo` attribute on `<body>`
   with the canonical repo URL so the "Edit on GitHub" links point at the
   right place.
3. In your repo's **Settings → Pages**, set the source to "GitHub Actions".
4. Push to `main`; the workflow deploys automatically.

---

## Initial data source

The first round of YAML files was seeded from the
[IDAC Capabilities Google Sheet](https://docs.google.com/spreadsheets/d/1r6JH0_5ROdSZ7I9_N4eSEHGbYgOO2QOwW_70IGo8RSg/edit)
using [`scripts/seed.py`](scripts/seed.py). After that point, the YAML
files in this repo are the source of truth — the spreadsheet is no longer
read by the dashboard.

The seed script is preserved for transparency / reproducibility, but
**should not be re-run** against existing files: it will overwrite any
human edits.

---

## License

TBD. Map tiles © OpenStreetMap contributors. Tabler is MIT-licensed.
