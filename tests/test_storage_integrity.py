from datetime import datetime, timezone
import json
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


def test_write_metadata_without_integrity_builds_checksums_from_verified_report(tmp_path):
    from myaichart.data.integrity import write_metadata

    payloads = write_metadata(
        tmp_path,
        collection={'symbol': 'XAUUSD', 'tick_count': 0},
        provenance={'source': 'dukascopy'},
    )

    assert 'integrity.json' in payloads
    assert 'checksums.json' in payloads
    assert payloads['checksums.json'] == payloads['integrity.json']['checksum_manifest']
    assert json.loads((tmp_path/'metadata'/'collection.json').read_text())['symbol'] == 'XAUUSD'


def test_repeated_raw_chunk_is_idempotent(tmp_path):
    store = RawTickStore(tmp_path)
    tick = NormalizedTick(
        symbol='XAUUSD', source='fixture', source_record_id='same',
        source_timestamp_utc=datetime(2026,9,25,8,tzinfo=timezone.utc),
        received_timestamp_utc=datetime(2026,9,25,8,tzinfo=timezone.utc),
        bid=3762.5, ask=3762.6,
    )
    store.append_chunk([tick])
    store.append_chunk([tick])
    got = list(store.iter_all('XAUUSD'))
    assert len(got) == 1
    assert got[0].source_record_id == 'same'


def test_verify_dataset_counts_ticks_through_store_api(tmp_path):
    store = RawTickStore(tmp_path)
    ticks = [
        NormalizedTick(
            symbol='XAUUSD', source='fixture', source_record_id=f'r{i}',
            source_timestamp_utc=datetime(2026,9,25,8,0,i,tzinfo=timezone.utc),
            received_timestamp_utc=datetime(2026,9,25,8,0,i,tzinfo=timezone.utc),
            bid=3762.5+i*.01, ask=3762.6+i*.01,
        ) for i in range(3)
    ]
    store.append_chunk(ticks)
    from myaichart.data.integrity import verify_dataset
    report = verify_dataset(tmp_path, 'XAUUSD')
    assert report['raw_tick_count'] == 3


def test_candle_store_writes_and_reads_processed_bars(tmp_path):
    from datetime import timedelta
    from myaichart.models import Candle, CandleState, BoundaryProfile
    from myaichart.data.candles import CandleStore
    ts=datetime(2026,9,25,7,40,tzinfo=timezone.utc)
    candle=Candle(symbol='XAUUSD',timeframe='M1',boundary_profile=BoundaryProfile.MYT_CALENDAR,
        time_open_utc=ts,time_close_utc=ts+timedelta(minutes=1),state=CandleState.FINAL,
        bid_open=10,bid_high=11,bid_low=9,bid_close=10.5,
        ask_open=10.2,ask_high=11.2,ask_low=9.2,ask_close=10.7,
        mid_open=10.1,mid_high=11.1,mid_low=9.1,mid_close=10.6,
        tick_count=4,quote_change_count=3)
    store=CandleStore(tmp_path)
    path=store.write('XAUUSD','M1',[candle])
    assert path.exists()
    got=list(store.read('XAUUSD','M1'))
    assert got==[candle]


def test_cli_aggregate_writes_processed_candles(tmp_path):
    from myaichart.cli import main
    store=RawTickStore(tmp_path)
    ticks=[
        NormalizedTick(symbol='XAUUSD',source='fixture',source_record_id='a',
            source_timestamp_utc=datetime(2026,9,25,8,0,1,tzinfo=timezone.utc),
            received_timestamp_utc=datetime(2026,9,25,8,0,1,tzinfo=timezone.utc),bid=10,ask=10.2),
        NormalizedTick(symbol='XAUUSD',source='fixture',source_record_id='b',
            source_timestamp_utc=datetime(2026,9,25,8,1,1,tzinfo=timezone.utc),
            received_timestamp_utc=datetime(2026,9,25,8,1,1,tzinfo=timezone.utc),bid=11,ask=11.2),
    ]
    store.append_chunk(ticks)
    assert main(['--data-dir',str(tmp_path),'aggregate','XAUUSD','--timeframes','M1','M5']) == 0
    processed=list((tmp_path/'processed').glob('xauusd_m1.*'))
    assert len(processed)==1
