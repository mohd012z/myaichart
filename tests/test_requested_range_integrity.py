from datetime import datetime, timezone
import json

from myaichart.data.integrity import verify_dataset
from myaichart.data.storage import RawTickStore
from myaichart.models import NormalizedTick


def _tick(ts: datetime, record_id: str = 'middle') -> NormalizedTick:
    return NormalizedTick(
        symbol='XAUUSD',
        source='dukascopy',
        source_record_id=record_id,
        source_timestamp_utc=ts,
        received_timestamp_utc=ts,
        bid=3762.5,
        ask=3762.6,
    )


def _assert_edge_gap_report(report):
    assert report['raw_tick_count'] == 1
    assert report['duplicate_count'] == 0
    assert report['missing_hour_count'] == 4
    assert report['scheduled_break_hour_count'] == 0
    assert report['weekend_closed_hour_count'] == 0
    assert report['unexplained_missing_hour_count'] == 4
    assert report['data_gap_count'] == 2


def test_requested_bounds_expose_leading_and_trailing_active_market_gaps(tmp_path):
    observed = datetime(2026, 9, 21, 10, 30, tzinfo=timezone.utc)
    start = datetime(2026, 9, 21, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 21, 12, 59, 59, tzinfo=timezone.utc)
    RawTickStore(tmp_path).append_chunk([_tick(observed)])

    report = verify_dataset(
        tmp_path,
        'XAUUSD',
        expected_start_utc=start,
        expected_end_utc=end,
        source_hint='dukascopy',
    )
    _assert_edge_gap_report(report)


def test_persisted_collection_bounds_are_used_when_explicit_bounds_are_omitted(tmp_path):
    observed = datetime(2026, 9, 21, 10, 30, tzinfo=timezone.utc)
    start = datetime(2026, 9, 21, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 21, 12, 59, 59, tzinfo=timezone.utc)
    RawTickStore(tmp_path).append_chunk([_tick(observed)])

    meta = tmp_path / 'metadata'
    meta.mkdir(parents=True, exist_ok=True)
    (meta / 'collection.json').write_text(json.dumps({
        'symbol': 'XAUUSD',
        'requested_start_utc': start.isoformat(),
        'requested_end_utc': end.isoformat(),
    }), encoding='utf-8')
    (meta / 'provenance.json').write_text(json.dumps({'source': 'dukascopy'}), encoding='utf-8')

    report = verify_dataset(tmp_path, 'XAUUSD')
    _assert_edge_gap_report(report)


def test_ticks_outside_requested_interval_do_not_satisfy_boundary_hour_coverage(tmp_path):
    start = datetime(2026, 9, 21, 10, 30, tzinfo=timezone.utc)
    end = datetime(2026, 9, 21, 12, 30, tzinfo=timezone.utc)
    RawTickStore(tmp_path).append_chunk([
        _tick(datetime(2026, 9, 21, 10, 15, tzinfo=timezone.utc), 'before-start'),
        _tick(datetime(2026, 9, 21, 11, 0, tzinfo=timezone.utc), 'inside'),
        _tick(datetime(2026, 9, 21, 12, 45, tzinfo=timezone.utc), 'after-end'),
    ])

    report = verify_dataset(
        tmp_path,
        'XAUUSD',
        expected_start_utc=start,
        expected_end_utc=end,
        source_hint='dukascopy',
    )

    assert report['raw_tick_count'] == 3
    assert report['missing_hour_count'] == 2
    assert report['unexplained_missing_hour_count'] == 2
    assert report['data_gap_count'] == 2
