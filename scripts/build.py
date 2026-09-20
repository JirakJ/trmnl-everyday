"""Build offline demo previews and importable ZIPs. Never reads private config."""
import argparse
import importlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from everyday.common import PLUGINS, clock, packet


def build(slug):
    directory = ROOT / "plugins" / slug
    data = importlib.import_module(f"everyday.{slug}").demo(clock({}))
    packet(data)
    (directory / ".trmnlp.yml").write_text(json.dumps({"time_zone": "Europe/Prague", "variables": data}))
    for command in ("lint", "build"):
        subprocess.run(["bundle", "exec", "trmnlp", command], cwd=directory, check=True)
    target = ROOT / "dist" / f"{slug}.zip"
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((directory / "src").iterdir()):
            if path.suffix in (".liquid", ".yml"):
                archive.write(path, path.name)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert "settings.yml" in archive.namelist()
        assert len(archive.namelist()) == 6
    print(f"Ready: {target.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("plugin", nargs="?", choices=PLUGINS)
    args = parser.parse_args()
    for slug in (args.plugin,) if args.plugin else PLUGINS:
        build(slug)
