"""Supported cities. Keys match the `choice` options used in workflow_dispatch later."""

CITIES: dict[str, tuple[float, float]] = {
    "berlin": (52.52, 13.41),
    "hamburg": (53.55, 9.99),
    "munich": (48.14, 11.58),
    "cologne": (50.94, 6.96),
}


def coordinates(city: str) -> tuple[float, float]:
    try:
        return CITIES[city.lower()]
    except KeyError:
        known = ", ".join(sorted(CITIES))
        raise ValueError(f"Unknown city '{city}'. Known cities: {known}") from None
