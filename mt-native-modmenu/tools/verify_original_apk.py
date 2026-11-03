#!/usr/bin/env python3
"""Fail-closed original APK metadata and integrity verification.
Does not edit the APK. APK v2/v3 verification must be performed by apksigner.
"""
import argparse
import hashlib
import json
import re
import struct
import sys
import zipfile

EXPECTED_SHA256 = "8ea942d8b48c27b8e3d569850a2279838d699c07d2dbfd198ccf89f4a4f2bfd3"
EXPECTED_PACKAGE = "net.metaquotes.metatrader5"
EXPECTED_VERSION = 6260

def manifest_attributes(data):
    def u16(i): return struct.unpack_from("<H",data,i)[0]
    def u32(i): return struct.unpack_from("<I",data,i)[0]
    if len(data)<8 or u16(0)!=3 or u32(4)>len(data):
        raise ValueError("invalid binary XML")
    pos=8
    strings=[]
    while pos<len(data):
        if pos+8>len(data): raise ValueError("truncated XML chunk")
        typ=u16(pos); head=u16(pos+2); size=u32(pos+4)
        if size<8 or pos+size>len(data): raise ValueError("invalid XML chunk size")
        if typ==1:
            count=u32(pos+8); flags=u32(pos+16); start=u32(pos+20)
            if count>100000: raise ValueError("excessive string count")
            offsets=[u32(pos+head+i*4) for i in range(count)]
            def length8(p):
                a=data[p]
                return (((a&127)<<8)|data[p+1],2) if a&128 else (a,1)
            def length16(p):
                a=u16(p)
                return (((a&32767)<<16)|u16(p+2),4) if a&32768 else (a,2)
            for offset in offsets:
                p=pos+start+offset
                if flags&256:
                    _,n=length8(p);p+=n
                    ln,n=length8(p);p+=n
                    strings.append(data[p:p+ln].decode("utf-8"))
                else:
                    ln,n=length16(p);p+=n
                    strings.append(data[p:p+ln*2].decode("utf-16le"))
        if typ==0x102 and strings:
            idx=u32(pos+20)
            if idx>=len(strings):raise ValueError("bad tag index")
            if strings[idx]=="manifest":
                attrs={}
                count=u16(pos+28);off=u16(pos+24);asz=u16(pos+26)
                if asz<20:raise ValueError("bad attribute size")
                for i in range(count):
                    q=pos+16+off+i*asz
                    name=strings[u32(q+4)]
                    raw=u32(q+8);kind=data[q+15];value=u32(q+16)
                    attrs[name]=strings[raw] if raw!=0xffffffff else (strings[value] if kind==3 else value)
                return attrs
        pos+=size
    raise ValueError("manifest element not found")

def audit(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    digest=h.hexdigest()
    with zipfile.ZipFile(path) as z:
        bad=z.testzip()
        attrs=manifest_attributes(z.read("AndroidManifest.xml"))
        entries=z.namelist()
    checks={
        "expected_sha256":digest==EXPECTED_SHA256,
        "zip_crc":bad is None,
        "expected_package":attrs.get("package")==EXPECTED_PACKAGE,
        "expected_version_code":attrs.get("versionCode")==EXPECTED_VERSION,
        "has_dex":"classes.dex" in entries,
        "has_v1_certificate": "META-INF/CERT.RSA" in entries,
    }
    return {"sha256":digest,"package":attrs.get("package"),
            "versionCode":attrs.get("versionCode"),"versionName":attrs.get("versionName"),
            "entry_count":len(entries),"checks":checks,"passed":all(checks.values()),
            "apk_v2_v3_verified":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("apk")
    a=p.parse_args()
    try:
        report=audit(a.apk)
        print(json.dumps(report,indent=2))
        sys.exit(0 if report["passed"] else 1)
    except (OSError,ValueError,zipfile.BadZipFile,struct.error,IndexError) as e:
        print(json.dumps({"passed":False,"error":str(e)}))
        sys.exit(2)
