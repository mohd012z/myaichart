from datetime import datetime, timezone
import lzma, struct
from myaichart.models import NormalizedTick
from myaichart.data.storage import RawTickStore
from myaichart.data.dukascopy import decode_bi5_ticks


def test_raw_tick_roundtrip_preserves_source_identity(tmp_path):
    store = RawTickStore(tmp_path)
    tick = NormalizedTick(
        symbol='XAUUSD', source='fixture', source_record_id='r1',
        source_timestamp_utc=datetime(2026,9,25,8,tzinfo=timezone.utc),
        received_timestamp_utc=datetime(2026,9,25,8,tzinfo=timezone.utc),
        bid=3762.5, ask=3762.6,
    )
    store.append_chunk([tick])
    got = list(store.iter_range('XAUUSD', tick.source_timestamp_utc, tick.source_timestamp_utc))
    assert got[0].source_record_id == 'r1'
    assert got[0].bid == 3762.5


def test_bi5_fixture_normalizes_three_rows_exactly():
    base = datetime(2026,9,25,8,tzinfo=timezone.utc)
    rows = []
    for ms, ask, bid, av, bv in [
        (100, 3762600, 3762500, 1.5, 2.0),
        (250, 3762650, 3762550, 1.2, 2.4),
        (900, 3762700, 3762600, 1.1, 2.1),
    ]:
        rows.append(struct.pack('>IIIff', ms, ask, bid, av, bv))
    payload = lzma.compress(b''.join(rows), format=lzma.FORMAT_ALONE)
    ticks = decode_bi5_ticks(payload, base, symbol='XAUUSD', price_scale=1000)
    assert len(ticks) == 3
    assert ticks[0].ask == 3762.6
    assert ticks[0].bid == 3762.5
    assert ticks[-1].source_timestamp_utc.microsecond == 900000


def test_integrity_report_contains_required_counts(tmp_path):
    from myaichart.data.integrity import verify_dataset
    report=verify_dataset(tmp_path)
    assert {'duplicate_count','data_gap_count','missing_hour_count','checksum_manifest'} <= report.keys()
