# Running on your own server

All collectors also work as manually invoked Python commands on macOS, Linux and
Windows. Automatic operation needs an always-on host. The examples below target
Linux with systemd; adapt the scheduler to your operating system.

## Linux service examples

The supplied units assume a dedicated existing `trmnl` OS user, the repository at
`/opt/trmnl-everyday`, and its installed Python virtual environment at `.venv`.
Keep code read-only for that user. Give it ownership of `private/` (mode 700) and
its files (mode 600). Use absolute source paths when reading data outside `private/`.

For each enabled plugin create `private/SLUG.json` from its documented example and
`private/SLUG.env` locally. The environment file contains `TRMNL_WEBHOOK_URL` and
only the source credentials needed by that plugin. Use systemd's `NAME=value`
format without `export`. Each plugin needs its own imported TRMNL webhook URL.
Do not put credentials in the service unit, command arguments or Git.

Install the units, then enable a specific plugin, for example Outside Window:

```sh
sudo cp deploy/systemd/trmnl-everyday@.service deploy/systemd/trmnl-everyday@.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now trmnl-everyday@outside.timer
sudo systemctl start trmnl-everyday@outside.service
sudo systemctl status trmnl-everyday@outside.service
```

Repeat for `family`, `workday`, `shifts`, `homelab`, `sales` or `maintenance` after
configuring each source. Enable only the plugins you intend to use. Replacing a CSV
or local ICS file remains your responsibility; a timer cannot create new source data.
The examples have not been installed on your server by this project.

For maintenance, also install and enable `trmnl-maintenance.service`. It listens
only on loopback. Configure your own HTTPS reverse proxy/VPN, preserving the host
from `confirmation_base_url`. For LAN-only access, make a systemd override of
`ExecStart` with the explicit LAN bind address described in the plugin's guide.

## Failure and recovery

Check the update timestamp on the screen and the service's exit status. A failed
provider read leaves the previous display intact. Homelab checks instead show
UNKNOWN/ERROR for failed checks, so a broken backup check cannot appear healthy.
Validation diagnostics exclude source response bodies and credentials.

Back up maintenance's SQLite database with SQLite's backup command/API while the
service runs, or stop the service before copying it. Its contents and environment
files are private. If a TRMNL webhook URL leaks, rotate it in TRMNL and replace the
local environment value. If a maintenance QR leaks, complete/change that task to
invalidate its pending links, or delete the corresponding `actions` entries locally.

## Verification commands

```sh
.venv/bin/python -m unittest discover -s tests -v
bundle install
.venv/bin/python scripts/build.py
npm ci
npx playwright install chromium
npm run check:layouts
PYTHON="$PWD/.venv/bin/python" node scripts/check_maintenance.cjs
```

The last command starts a temporary loopback server with synthetic tasks, decodes
its QR, confirms completion through Chromium, checks persisted state and shuts down.
No real TRMNL account, calendars or sales exports are used by these checks.
