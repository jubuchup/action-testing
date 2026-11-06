from weather_pipeline import transform


def test_to_frame_shape_and_columns(raw_payload):
    df = transform.to_frame(raw_payload)
    assert list(df.columns) == transform.COLUMNS
    assert len(df) == 5


def test_mean_temperature_is_average_of_min_and_max(raw_payload):
    df = transform.to_frame(raw_payload)
    # 2026-11-01: (11.2 + 4.2) / 2 = 7.7
    assert df.loc[0, "temp_mean_c"] == 7.7


def test_rainy_days_use_threshold(raw_payload):
    df = transform.to_frame(raw_payload)
    # precipitation: 0.0, 2.4, 0.0, 0.6, 5.1 -> rainy (>= 1mm) on day 2 and day 5
    assert df["is_rainy_day"].tolist() == [False, True, False, False, True]


def test_run_writes_csv_that_roundtrips(raw_file, tmp_path):
    out = tmp_path / "clean.csv"
    transform.run(raw_file, out)
    loaded = transform.load(out)
    assert len(loaded) == 5
    assert loaded["city"].unique().tolist() == ["berlin"]
