#!/usr/bin/env python3
"""Rewrite only manifest package-scoped identifiers in an apktool-decoded clone.
Never alter the original APK or embedded broker credentials.
"""
import argparse
import pathlib
import sys
import xml.etree.ElementTree as ET

A = "{http://schemas.android.com/apk/res/android}"
SCOPED = {"authorities", "permission", "readPermission", "writePermission",
          "process", "taskAffinity", "targetPackage", "name"}
def rewrite(src, dest, target="com.msa.mt5research"):
    root = ET.parse(src).getroot()
    old = root.get("package")
    if not old or old == target or not target or not all(x.isidentifier() for x in target.split(".")):
        raise ValueError("invalid original/clone package identity")
    root.set("package", target)
    for element in root.iter():
        for key, value in list(element.attrib.items()):
            if not key.startswith(A) or key[len(A):] not in SCOPED:
                continue
            attr = key[len(A):]
            if attr == "name" and element.tag in ("activity","activity-alias","service","receiver","provider","application","instrumentation"):
                # Class names are bytecode identities, not package identities. Do not rewrite.
                continue
            if value == old or value.startswith(old + ".") or value.startswith(old + ":"):
                element.set(key, target + value[len(old):])
            elif attr == "authorities":
                parts = value.split(";")
                element.set(key, ";".join(target+p[len(old):] if p==old or p.startswith(old+".") else p for p in parts))
    out = pathlib.Path(dest)
    if pathlib.Path(src).resolve() == out.resolve():
        raise ValueError("refuse in-place modification")
    out.parent.mkdir(parents=True,exist_ok=True)
    ET.register_namespace("android","http://schemas.android.com/apk/res/android")
    ET.ElementTree(root).write(out,encoding="utf-8",xml_declaration=True)
    return old,target

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("original_manifest")
    parser.add_argument("clone_manifest")
    parser.add_argument("--package",default="com.msa.mt5research")
    args=parser.parse_args()
    try:
        print("package rewrite:",*rewrite(args.original_manifest,args.clone_manifest,args.package))
    except (OSError,ET.ParseError,ValueError) as e:
        print("ERROR:",e,file=sys.stderr)
        sys.exit(1)
