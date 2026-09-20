# Release verification

Verified locally on 20 September 2026 with Python 3.14, the pinned official
`trmnl_preview` 0.12.0 renderer and Chromium/Chrome browser automation. GitHub Actions
repeats the Python checks, template builds, all layout checks and the confirmation
flow on Linux with Python 3.13.

| Check | Result |
| --- | --- |
| Focused Python regression tests | 11 passed |
| Official TRMNL template lint/build | 7 plugins passed |
| Browser layout checks | 28 layouts passed at the original 800×480 screen size |
| Maintenance QR decoding | All four layouts decoded successfully |
| Actual confirmation HTTP service | GET preserved state; browser POST persisted completion; old link invalidated |
| Webhook payload budget | All demos fit 2000 bytes; oversized payloads are refused |
| Long maintenance hostname | 1460-byte payload, 57-module QR including quiet zone |
| Live weather provider read | Open-Meteo forecast fetched successfully for the example city |
| Secret scan | Git history and staged files passed Gitleaks |
| Python dependencies | Pinned runtime requirements passed pip-audit |
| Node dependencies | npm audit reported no known vulnerabilities |

Regression cases cover complete outdoor activity windows, missing/invalid weather,
calendar recurrence exclusions and cancellation, private calendar data, overlapping
meetings, weekends, overnight shifts and daylight-saving transitions, backup age,
missing snapshots, CSV duplicates/refunds/currencies/month boundaries, month-end
maintenance dates, confirmation expiry, changed settings, CSRF, hostile Host/Origin
headers, HTML escaping and link reuse. Tests use synthetic calendars and sales.

Screenshots in `docs/previews/` contain **synthetic demo data**. Browser layout checks
look for overflow, script errors and QR decoding; they do not establish readability
under all lighting conditions or on every TRMNL device size.

## Not yet verified

- Import and webhook delivery inside an actual TRMNL account, physical e-paper
  refresh and camera scanning from a physical display.
- A user's Microsoft tenant/ICS feed, private sales exports, backup repository or
  home-server installation. Microsoft OAuth and automatic sales-report retrieval
  are outside this release's implementation.
- TRMNL Recipe catalog publication, approval or Creator Fund eligibility.

These checks establish the repository's implemented behavior. They do not promise
uninterrupted third-party APIs, zero future vulnerabilities or backup restore integrity.
