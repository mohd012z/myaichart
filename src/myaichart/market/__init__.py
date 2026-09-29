"""Market Hub — provider adapters, tick quality, health engine.

Sole market-truth layer for the BBMA cluster. Every provider adapter emits
``MarketTick`` (raw, provider-shaped); the hub normalizes to
``myaichart.models.NormalizedTick`` (quality-tagged), validates, sequences,
feeds the candle engine, tracks provider health, and broadcasts a single
canonical stream. Provider identity is always carried (provider +
provider_symbol) so futures-proxy and spot series are never blended silently.
"""
