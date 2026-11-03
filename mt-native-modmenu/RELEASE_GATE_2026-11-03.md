# MT5 Research Clone — Release Gate (2026-11-03)

**Decision: BLOCKED — do not publish an APK.**

Target package: `com.msa.mt5research`; original MT5 500.6260 must remain installed and unchanged.

## Confirmed
- The supplied original APK passed ZIP integrity and contains 4,282 entries, including `classes.dex`.
- SHA-256 original: `8ea942d8b48c27b8e3d569850a2279838d699c07d2dbfd198ccf89f4a4f2bfd3`.
- Local pure Kotlin smoke suite passed 12/12; **not an Android device test**.
- GitHub Android CI run #126 failed because a test expected a clone with the unchanged shared `third.party` provider authority to pass. Test corrected in `4ee49e4d234f4f194c91b2ee0a9d3e0ab5b16d25`; rerun not yet verified.

## Required gates before publishing
1. Decode actual APK, rewrite package-scoped identities, audit every provider authority and permission.
2. Verify chart host integration, compile DEX and package an isolated clone.
3. Verify zipalign, APK signature and artifact SHA-256.
4. Install alongside official MT5; verify both package IDs remain installed.
5. Smoke-test launch, chart navigation, ModeMenu controls, lifecycle and crash logs.
6. Verify broker discovery and normal login on user-controlled device with demo credentials entered locally; never upload passwords.
7. Verify research overlays, OHLC freshness and chart alignment.
8. Record real test evidence and build logs.

No Android SDK build tools, apktool, adb or device were available locally. No signed clone APK or broker login test exists. Preserve `main`, credentials and RM0 billing.
