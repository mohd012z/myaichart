#!/usr/bin/env bash
set -Eeuo pipefail
# Verify reproducible Android SDK prerequisites. Does not download tools or sign APKs.
BUILD_TOOLS_VERSION="${BUILD_TOOLS_VERSION:-35.0.0}"
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [[ -z "$SDK" ]]; then echo "FAIL: ANDROID_HOME/ANDROID_SDK_ROOT missing" >&2; exit 2; fi
if [[ ! -d "$SDK/build-tools/$BUILD_TOOLS_VERSION" ]]; then
  echo "FAIL: pinned build-tools $BUILD_TOOLS_VERSION missing" >&2; exit 2
fi
for cmd in aapt aapt2 apksigner zipalign d8; do
  file="$SDK/build-tools/$BUILD_TOOLS_VERSION/$cmd"
  [[ -x "$file" ]] || { echo "FAIL: $file missing" >&2; exit 2; }
  echo "FOUND $cmd $file"
done
[[ -f "$SDK/platforms/android-35/android.jar" ]] || { echo "FAIL: android-35 platform missing" >&2; exit 2; }
java -version 2>&1 | head -3
"$SDK/build-tools/$BUILD_TOOLS_VERSION/aapt" version
"$SDK/build-tools/$BUILD_TOOLS_VERSION/zipalign" -h 2>&1 | head -2 || true
"$SDK/build-tools/$BUILD_TOOLS_VERSION/apksigner" version
echo "PASS: SDK prerequisites present. APK build, signing and device tests not implied."
