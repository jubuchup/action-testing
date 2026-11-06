import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def raw_payload() -> dict:
    """A recorded Open-Meteo response, so tests never hit the network."""
    return json.loads((FIXTURES / "raw_berlin.json").read_text(encoding="utf-8"))


@pytest.fixture
def raw_file(tmp_path: Path, raw_payload: dict) -> Path:
    path = tmp_path / "raw.json"
    path.write_text(json.dumps(raw_payload), encoding="utf-8")
    return path
