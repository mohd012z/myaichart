#!/usr/bin/env bash
set -Eeuo pipefail
# Usage: sign_verify_clone.sh unsigned-clone.apk signed-clone.apk original.apk
# Requires Android SDK build-tools (apksigner, zipalign, aapt) and ephemeral signing key.
# No secrets are printed or committed. The source and official APK are read-only.
if [[ $# -ne 3 ]]; then echo "usage: $0 UNSIGNED SIGNED ORIGINAL" >&2; exit 2; fi
unsigned="$1"; signed="$2"; original="$3"
for cmd in apksigner zipalign aapt keytool sha256sum; do command -v "$cmd" >/dev/null || { echo "missing tool: $cmd" >&2; exit 2; }; done
[[ -f "$unsigned" && -f "$original" ]] || { echo "missing APK input" >&2; exit 2; }
[[ "$(realpath "$unsigned")" != "$(realpath "$original")" ]] || { echo "refuse to sign original" >&2; exit 2; }
[[ "$(realpath -m "$signed")" != "$(realpath "$original")" ]] || { echo "refuse to overwrite original" >&2; exit 2; }
[[ "$(realpath -m "$signed")" != "$(realpath "$unsigned")" ]] || { echo "refuse in-place signing" >&2; exit 2; }
package_of() { aapt dump badging "$1" | sed -n "s/^package: name='\([^']*\)'.*/\1/p" | head -1; }
original_package="$(package_of "$original")"
clone_package="$(package_of "$unsigned")"
[[ -n "$original_package" && "$clone_package" == "com.msa.mt5research" && "$clone_package" != "$original_package" ]] || {
  echo "package identity mismatch; refuse signing" >&2; exit 1;
}
original_hash="$(sha256sum "$original" | cut -d' ' -f1)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
# Use a unique ephemeral certificate. It is not an update key and must not be used for production upgrades.
keytool -genkeypair -noprompt -keystore "$work/clone.p12" -storetype PKCS12 \
  -alias clone -keyalg RSA -keysize 3072 -validity 365 \
  -dname "CN=MT5 Research Local Test" -storepass changeit -keypass changeit >/dev/null 2>&1
zipalign -f -p 4 "$unsigned" "$work/aligned.apk"
apksigner sign --ks "$work/clone.p12" --ks-key-alias clone --ks-pass pass:changeit \
  --key-pass pass:changeit --out "$signed" "$work/aligned.apk"
zipalign -c -p 4 "$signed"
apksigner verify --verbose --print-certs "$signed"
[[ "$(package_of "$signed")" == "$clone_package" ]] || { echo "signed package changed" >&2; exit 1; }
[[ "$(sha256sum "$original" | cut -d' ' -f1)" == "$original_hash" ]] || { echo "original changed" >&2; exit 1; }
printf 'ORIGINAL_PACKAGE=%s\nCLONE_PACKAGE=%s\nORIGINAL_SHA256=%s\nSIGNED_CLONE_SHA256=%s\n' \
  "$original_package" "$clone_package" "$original_hash" "$(sha256sum "$signed" | cut -d' ' -f1)"
echo "SIGNATURE_VERIFIED; DEVICE_INSTALL_AND_LOGIN_NOT_VERIFIED"
