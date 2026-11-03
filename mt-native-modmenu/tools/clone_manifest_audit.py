#!/usr/bin/env python3
"""Audit decoded Android manifests before attempting an MT5 research clone.

Requires apktool-decoded AndroidManifest.xml; never edits the official APK.
"""
import argparse
import json
import sys
import xml.etree.ElementTree as ET

ANDROID = "{http://schemas.android.com/apk/res/android}"
ATTRS = ("authorities", "permission", "readPermission", "writePermission",
         "process", "taskAffinity", "targetPackage")
COMPONENTS = ("activity", "activity-alias", "service", "receiver", "provider")

def audit(source_xml, clone_xml, expected_package):
    original = ET.parse(source_xml).getroot()
    clone = ET.parse(clone_xml).getroot()
    old_pkg = original.get("package")
    new_pkg = clone.get("package")
    errors = []
    if not old_pkg or not new_pkg:
        errors.append("MISSING_PACKAGE")
    if old_pkg == new_pkg:
        errors.append("UNCHANGED_PACKAGE")
    if new_pkg != expected_package:
        errors.append("UNEXPECTED_CLONE_PACKAGE")
    if not expected_package or expected_package == old_pkg:
        errors.append("INVALID_EXPECTED_PACKAGE")
    original_components = {}
    clone_components = {}
    for root, dest in ((original, original_components), (clone, clone_components)):
        for el in root.iter():
            if el.tag in COMPONENTS:
                key = (el.tag, el.get(ANDROID + "name"))
                dest[key] = el
    for key, src in original_components.items():
        dst = clone_components.get(key)
        if dst is None:
            errors.append("MISSING_COMPONENT:" + str(key))
            continue
        for attr in ATTRS:
            before = src.get(ANDROID + attr)
            after = dst.get(ANDROID + attr)
            if not before or not after:
                continue
            if attr == "authorities":
                a = set(before.split(";"))
                b = set(after.split(";"))
                if a & b:
                    errors.append("PROVIDER_AUTHORITY_COLLISION:" + ",".join(sorted(a & b)))
            elif attr in ("permission", "readPermission", "writePermission", "taskAffinity", "process"):
                if before.startswith(old_pkg) and after == before:
                    errors.append("UNREWRITTEN_" + attr.upper() + ":" + before)
    old_permissions = {e.get(ANDROID + "name") for e in original.findall("permission")}
    new_permissions = {e.get(ANDROID + "name") for e in clone.findall("permission")}
    for permission in sorted(old_permissions & new_permissions):
        if permission:
            errors.append("DECLARED_PERMISSION_COLLISION:" + permission)
    return {"original_package": old_pkg, "clone_package": new_pkg,
            "component_count_original": len(original_components),
            "component_count_clone": len(clone_components),
            "errors": sorted(set(errors)), "passed": not errors}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("original")
    p.add_argument("clone")
    p.add_argument("--package", default="com.msa.mt5research")
    a = p.parse_args()
    try:
        result = audit(a.original, a.clone, a.package)
    except (ET.ParseError, OSError, ValueError) as exc:
        print(json.dumps({"passed": False, "errors": [str(exc)]}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
