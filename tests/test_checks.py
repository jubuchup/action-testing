from weather_pipeline import checks, transform


def _failed(results):
    return {r.name for r in results if not r.passed}


def test_clean_data_passes_all_checks(raw_payload):
    df = transform.to_frame(raw_payload)
    assert _failed(checks.run_checks(df)) == set()


def test_too_few_rows_fails(raw_payload):
    df = transform.to_frame(raw_payload).head(2)
    assert _failed(checks.run_checks(df, min_rows=3)) == {"enough rows"}


def test_max_below_min_fails(raw_payload):
    df = transform.to_frame(raw_payload)
    df.loc[0, "temp_max_c"] = -10.0
    assert "max >= min temperature" in _failed(checks.run_checks(df))


def test_negative_precipitation_fails(raw_payload):
    df = transform.to_frame(raw_payload)
    df.loc[1, "precipitation_mm"] = -1.0
    assert "non-negative precipitation" in _failed(checks.run_checks(df))
