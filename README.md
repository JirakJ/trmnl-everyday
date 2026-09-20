# TRMNL Everyday

Seven focused, open-source plugins for an e-paper display. Each plugin has its own
importable TRMNL ZIP, four layouts, an offline demo, and a small data collector.
The collector runs on your computer or home server; no account with us is needed.

## Plugins

| Plugin | Purpose |
| --- | --- |
| [Outside Window](plugins/outside) | Find a suitable time to walk, run or cycle |
| [Family Day](plugins/family) | Shared agenda, pickups and tomorrow's essentials |
| [Workday Windows](plugins/workday) | Find uninterrupted time between meetings |
| [Shift Together](plugins/shifts) | Shift rotas, exceptions and shared time off |
| [Homelab Watch](plugins/homelab) | Disk space, service health and backup freshness |
| [Digital Product Sales](plugins/sales) | Sales, renewals and refunds from local CSV exports |

## Install

Requires Python 3.11+ and a TRMNL account with Private Plugin access. The collector
must run periodically on an always-on computer for automatic updates.

```sh
git clone https://github.com/JirakJ/trmnl-everyday.git
cd trmnl-everyday
python3 -m venv .venv
.venv/bin/pip install -e .
mkdir -p private
chmod 700 private
cp plugins/outside/config.example.json private/outside.json
.venv/bin/python -m everyday outside --config private/outside.json
```

1. Download the plugin ZIP from [Releases](https://github.com/JirakJ/trmnl-everyday/releases).
2. In TRMNL, open **Plugins → Private Plugin → Import new** and select the ZIP.
3. Copy its webhook URL into the `TRMNL_WEBHOOK_URL` environment variable locally.
   Treat it as a password. Do not commit it or paste it into an issue.
4. Edit your `private/*.json` configuration, then run the same command with `--push`.
5. Schedule it every 15 minutes using your OS scheduler. Each plugin has a different webhook URL.

Without `--push`, the collector only prints the screen JSON. `--demo` uses synthetic
data, requires no accounts or network, and cannot be pushed. Normal failures return
a non-zero exit code and preserve the previous screen. Check the displayed update
time: an e-paper screen can retain old information when your collector is offline.

## Develop and verify

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m everyday outside --demo
bundle install
.venv/bin/python scripts/build.py outside
```

Ruby 4.0+ is required for the pinned official `trmnlp` preview tool. The build
creates a synthetic `.trmnlp.yml`, renders all four layouts under `_build/`, and
packages `dist/outside.zip`. To preview with automatic reload:

```sh
cd plugins/outside
bundle exec trmnlp serve
```

Preview files and local data are ignored by Git. Release ZIPs contain only templates
and settings, with no demo events, credentials or private configuration. Templates
escape dynamic text. The collector refuses redirects and enforces a conservative
2000-byte webhook payload limit.

## Distribution and privacy

MIT-licensed source code does not grant rights to third-party data services. Review
each plugin's data-provider requirements. Importing these plugins is separate from
publication in the TRMNL Recipe catalog; catalog approval and Creator Fund eligibility
are handled by TRMNL. This project is independent of TRMNL.

Your configured providers receive the requests needed to retrieve your data. TRMNL
receives the compact screen payload. There is no telemetry or developer-operated
backend. Keep local configuration, calendar feeds and generated personal previews private.

See [TRMNL import documentation](https://help.trmnl.com/en/articles/10542599-importing-and-exporting-private-plugins)
and [webhook documentation](https://docs.trmnl.com/go/private-plugins/webhooks).
