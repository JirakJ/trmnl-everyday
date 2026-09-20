import argparse
import importlib
import json
import sys
from .common import PLUGINS, clock, packet, push, read_config


def main():
    parser = argparse.ArgumentParser(description="Collect a TRMNL screen. Nothing is sent unless --push is used.")
    parser.add_argument("plugin", choices=PLUGINS)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--config", help="Local JSON configuration (keep in private/)")
    source.add_argument("--demo", action="store_true", help="Offline synthetic data, visibly labelled")
    parser.add_argument("--push", action="store_true", help="Send to TRMNL_WEBHOOK_URL")
    args = parser.parse_args()
    try:
        module = importlib.import_module(f"everyday.{args.plugin}")
        config = {} if args.demo else read_config(args.config)
        now = clock(config)
        data = module.demo(now) if args.demo else module.collect(config, now)
        packet(data)
        if args.push:
            push(data)
            print("TRMNL accepted the screen data.")
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError) as error:
        # Source parsing can include private values; only known safe validation messages are displayed.
        print(f"Failed ({type(error).__name__}); check configuration and source availability. No new screen was sent.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
