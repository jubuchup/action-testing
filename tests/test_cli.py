from weather_pipeline import cli


def test_transform_check_report_end_to_end(raw_file, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "abcdef1234567890")
    clean = tmp_path / "clean.csv"
    site = tmp_path / "site" / "index.html"

    assert cli.main(["transform", "--input", str(raw_file), "--out", str(clean)]) == 0
    assert cli.main(["check", "--input", str(clean)]) == 0
    assert cli.main(["report", "--input", str(clean), "--out", str(site), "--title", "T"]) == 0

    html = site.read_text(encoding="utf-8")
    assert "<title>T</title>" in html
    assert "abcdef1" in html  # commit SHA from the CI environment ends up in the report
    assert "all checks passed" in capsys.readouterr().out


def test_check_exits_1_on_bad_data(raw_file, tmp_path):
    clean = tmp_path / "clean.csv"
    cli.main(["transform", "--input", str(raw_file), "--out", str(clean)])
    assert cli.main(["check", "--input", str(clean), "--min-rows", "100"]) == 1
