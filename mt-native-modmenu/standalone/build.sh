#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
[[ -n "$SDK" ]] || { echo "ANDROID_HOME missing" >&2; exit 2; }
BT="$SDK/build-tools/35.0.0"
for x in aapt2 d8 zipalign apksigner; do [[ -x "$BT/$x" ]] || { echo "missing $x" >&2; exit 2; }; done
[[ -f "$SDK/platforms/android-35/android.jar" ]] || exit 2
OUT="${1:-$ROOT/mt-native-modmenu/standalone/build}"
mkdir -p "$OUT/classes" "$OUT/dex"
javac -source 8 -target 8 -classpath "$SDK/platforms/android-35/android.jar" -d "$OUT/classes" \
  "$ROOT/mt-native-modmenu/src/Mt5ResearchMenu.java" \
  "$ROOT/mt-native-modmenu/standalone/MainActivity.java"
"$BT/d8" --min-api 28 --lib "$SDK/platforms/android-35/android.jar" --output "$OUT/dex" \
  $(find "$OUT/classes" -name '*.class' -type f)
"$BT/aapt2" link -o "$OUT/unsigned.apk" -I "$SDK/platforms/android-35/android.jar" \
  --manifest "$ROOT/mt-native-modmenu/standalone/AndroidManifest.xml" --min-sdk-version 28 --target-sdk-version 35
(cd "$OUT/dex" && zip -q -u "$OUT/unsigned.apk" classes.dex) 2>/dev/null || \
  "$BT/aapt" add "$OUT/unsigned.apk" "$OUT/dex/classes.dex"
"$BT/zipalign" -f -p 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
KEY="$OUT/test-signing.p12"
if [[ ! -f "$KEY" ]]; then
  keytool -genkeypair -noprompt -storetype PKCS12 -keystore "$KEY" -alias research \
    -storepass changeit -keypass changeit -keyalg RSA -keysize 3072 -validity 3650 \
    -dname "CN=MSA Research Local Testing" >/dev/null 2>&1
fi
"$BT/apksigner" sign --ks "$KEY" --ks-key-alias research --ks-pass pass:changeit \
  --key-pass pass:changeit --out "$OUT/msa-chart-research.apk" "$OUT/aligned.apk"
"$BT/apksigner" verify --verbose --print-certs "$OUT/msa-chart-research.apk"
"$BT/aapt" dump badging "$OUT/msa-chart-research.apk" | grep "^package: name='com.msa.mt5research'"
sha256sum "$OUT/msa-chart-research.apk"
echo "Build verified; device installation NOT verified."
