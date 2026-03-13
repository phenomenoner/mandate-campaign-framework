#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _runtime_lib import framework_root_from_script, validate_mandate_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a mandate against kernel v0.1 fields.")
    parser.add_argument("mandate", help="Path to mandate YAML")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    framework_root = framework_root_from_script(__file__)
    result = validate_mandate_file(Path(args.mandate).resolve(), framework_root)

    payload = {
        "ok": result.ok,
        "errors": result.errors,
        "warnings": result.warnings,
        "framework_root": str(framework_root),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if result.ok:
            print("validate-mandate: OK")
            print(f"mandate_id: {result.mandate['mandate_id']}")
            print(f"adapter: {result.mandate['adapter']}")
            if result.warnings:
                print("warnings:")
                for warning in result.warnings:
                    print(f"- {warning}")
        else:
            print("validate-mandate: FAIL", file=sys.stderr)
            for error in result.errors:
                print(f"- {error}", file=sys.stderr)
            for warning in result.warnings:
                print(f"warning: {warning}", file=sys.stderr)

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
