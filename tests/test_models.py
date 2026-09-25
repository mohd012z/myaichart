from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from myaichart.models import NormalizedTick, CandleState, BoundaryProfile


def test_normalized_tick_requires_ask_not_below_bid():
    with pytest.raises(ValidationError):
        NormalizedTick(
            symbol='XAUUSD', source='fixture', source_record_id='1',
            source_timestamp_utc=datetime(2026,9,25,8,0,tzinfo=timezone.utc),
            received_timestamp_utc=datetime(2026,9,25,8,0,tzinfo=timezone.utc),
            bid=3762.55, ask=3762.50,
        )


def test_tick_mid_and_spread_are_derived():
    t = NormalizedTick(
        symbol='XAUUSD', source='fixture', source_record_id='2',
        source_timestamp_utc=datetime(2026,9,25,8,0,tzinfo=timezone.utc),
        received_timestamp_utc=datetime(2026,9,25,8,0,tzinfo=timezone.utc),
        bid=3762.50, ask=3762.58,
    )
    assert t.mid == pytest.approx(3762.54)
    assert t.spread_price == pytest.approx(0.08)


def test_enums_include_realtime_states():
    assert CandleState.LIVE.value == 'LIVE'
    assert BoundaryProfile.MYT_CALENDAR.value == 'MYT_CALENDAR'
