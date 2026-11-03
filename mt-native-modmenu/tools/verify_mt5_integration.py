#!/usr/bin/env python3
"""Fail-closed MT5 integration evidence gate. No executable patching."""
import argparse
import json
import pathlib
import sys

REQUIRED = (
    "chart_host_class",
    "chart_host_method",
    "verified_parent_type",
    "injection_callsite",
    "dex_patch_artifact",
    "signed_apk",
    "apk_signature_verified",
    "package_identity_verified",
    "device_launch_verified",
)
def verify(report):
    missing = [key for key in REQUIRED if not report.get(key)]
    if report.get("chart_host_class") == "ChartSurface" and not report.get("injection_callsite"):
        if "injection_callsite" not in missing: missing.append("injection_callsite")
    return {"ready": not missing, "missing": missing}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("report", type=pathlib.Path)
    args = p.parse_args()
    try:
        evidence = json.loads(args.report.read_text(encoding="utf-8"))
        result = verify(evidence)
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"ready": False, "error": str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["ready"] else 1

if __name__ == "__main__":
    sys.exit(main())
