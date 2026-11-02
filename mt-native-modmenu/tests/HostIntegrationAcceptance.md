# Host integration falsification checklist

- ChartSurface is actually present in the active chart View hierarchy, not just the APK DEX.
- ChartSurface's immediate parent and root content ViewGroup are observed at runtime.
- TextureView is available before drawing and remains valid after rotation/background/resume.
- Chart bounds are measured in the same local coordinate space as the overlay.
- Price/time projection is independently calibrated at left, center and right candle positions.
- Pan, pinch-zoom, timeframe change and symbol change invalidate stale snapshots.
- Historical candles are strictly ordered, closed and sourced from an authorized feed.
- Overlay is disabled when the host gate rejects missing or stale snapshots.
- Touch handling does not block MT5 chart gestures.
- Android source compilation and real APK/device installation are independently verified.
- Original proprietary APK, signing keys and broker credentials are never committed.
