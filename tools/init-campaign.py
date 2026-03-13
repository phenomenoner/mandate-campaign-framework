#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from _runtime_lib import (
    build_initial_receipt,
    build_initial_state,
    dump_json,
    framework_root_from_script,
    load_adapter_defaults,
    validate_mandate_file,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a campaign from a validated mandate.")
    parser.add_argument("mandate", help="Path to mandate YAML")
    parser.add_argument(
        "--campaigns-dir",
        default=None,
        help="Optional campaigns root (defaults to <framework>/campaigns)",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing campaign directory")
    args = parser.parse_args()

    framework_root = framework_root_from_script(__file__)
    result = validate_mandate_file(Path(args.mandate).resolve(), framework_root)
    if not result.ok:
        print("init-campaign: FAIL (mandate validation)", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    mandate = result.mandate
    adapter_defaults = load_adapter_defaults(framework_root, mandate["adapter"])
    campaigns_root = (
        Path(args.campaigns_dir).resolve()
        if args.campaigns_dir
        else framework_root / "campaigns"
    )
    campaign_dir = campaigns_root / mandate["mandate_id"]

    if campaign_dir.exists():
        if not args.force:
            print(f"init-campaign: FAIL (campaign exists: {campaign_dir})", file=sys.stderr)
            return 1
        shutil.rmtree(campaign_dir)

    receipts_dir = campaign_dir / "receipts"
    artifacts_dir = campaign_dir / "artifacts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    canonical_mandate_path = campaign_dir / "MANDATE.yaml"
    state_path = campaign_dir / "CAMPAIGN_STATE.json"
    receipt_path = receipts_dir / "000_campaign_created.json"

    shutil.copyfile(Path(args.mandate).resolve(), canonical_mandate_path)
    dump_json(state_path, build_initial_state(mandate, adapter_defaults))
    dump_json(receipt_path, build_initial_receipt(mandate))

    print("init-campaign: OK")
    print(f"campaign_dir: {campaign_dir}")
    print(f"mandate: {canonical_mandate_path}")
    print(f"state: {state_path}")
    print(f"receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
