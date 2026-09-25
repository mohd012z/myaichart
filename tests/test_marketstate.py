from myaichart.marketstate.classifier import classify_interval


def test_reference_holiday_does_not_override_observed_ticks():
    result=classify_interval(ticks_present=True,reference_state='HOLIDAY',outage=False,weekend=False)
    assert result.observed_market_state=='OPEN'
    assert result.reference_market_state=='HOLIDAY'


def test_no_ticks_known_outage_is_source_outage():
    result=classify_interval(ticks_present=False,reference_state=None,outage=True,weekend=False)
    assert result.observed_market_state=='SOURCE_OUTAGE'
