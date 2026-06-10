"""Pure outfit-advice logic for the What Should I Wear? integration.

This module is deliberately free of Home Assistant imports so the decision
rules can be reasoned about (and unit-tested) in isolation. The coordinator
turns a weather forecast into a :class:`WeatherSnapshot`; the entities turn a
snapshot plus a person's :class:`PersonProfile` into an :class:`Advice`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .const import (
    DEFAULT_JACKET_MAX_TEMP,
    DEFAULT_RAIN_PROB_THRESHOLD,
    DEFAULT_SANDALS_MIN_TEMP,
    DEFAULT_UMBRELLA_OVER_RAINJACKET,
    WIND_UMBRELLA_USELESS,
)

RAIN_JACKET = "rain jacket"
UMBRELLA = "umbrella"


@dataclass(frozen=True)
class ForecastHour:
    """A single upcoming hourly forecast point, within the lookahead window."""

    datetime: datetime
    temperature: float | None
    precipitation_probability: float | None
    wind_speed: float | None
    condition: str | None


@dataclass
class WeatherSnapshot:
    """Everything the advice needs about the weather, person-independent.

    ``temp_now``/``condition_now`` come from the weather entity's current
    state; ``hours`` are the future forecast points that fall inside the
    configured lookahead window (current hour included as the first point when
    the forecast provides it).
    """

    temp_now: float | None
    condition_now: str | None
    hours: list[ForecastHour] = field(default_factory=list)
    lookahead_hours: int = 6

    @property
    def temperatures(self) -> list[float]:
        """All known temperatures across now + the lookahead window."""
        values = [h.temperature for h in self.hours if h.temperature is not None]
        if self.temp_now is not None:
            values.append(self.temp_now)
        return values

    @property
    def temp_min(self) -> float | None:
        """Coldest it is expected to get across the window."""
        values = self.temperatures
        return min(values) if values else None

    @property
    def temp_max(self) -> float | None:
        """Warmest it is expected to get across the window."""
        values = self.temperatures
        return max(values) if values else None

    @property
    def max_precip_prob(self) -> float | None:
        """Highest precipitation probability across the window (percent)."""
        values = [
            h.precipitation_probability
            for h in self.hours
            if h.precipitation_probability is not None
        ]
        return max(values) if values else None

    @property
    def max_wind(self) -> float | None:
        """Strongest wind across the window."""
        values = [h.wind_speed for h in self.hours if h.wind_speed is not None]
        return max(values) if values else None


@dataclass(frozen=True)
class PersonProfile:
    """A person's comfort thresholds. Built from their config subentry."""

    name: str
    sandals_min_temp: float = DEFAULT_SANDALS_MIN_TEMP
    jacket_max_temp: float = DEFAULT_JACKET_MAX_TEMP
    rain_prob_threshold: float = DEFAULT_RAIN_PROB_THRESHOLD
    umbrella_over_rainjacket: bool = DEFAULT_UMBRELLA_OVER_RAINJACKET


@dataclass
class Advice:
    """The verdict for one person, given a weather snapshot."""

    sandals_ok: bool
    rain_needed: bool
    jacket_needed: bool
    rain_gear: str  # "umbrella", "rain jacket", or "" when no rain expected
    rain_starts: datetime | None
    temp_now: float | None
    temp_min: float | None
    temp_max: float | None
    max_precip_prob: float | None
    max_wind: float | None
    recommendation: str
    message: str


def _fmt_temp(value: float | None) -> str:
    """Render a temperature as a tidy ``21°`` string, or ``?`` when unknown."""
    if value is None:
        return "?"
    return f"{round(value)}°"


def evaluate(snapshot: WeatherSnapshot, profile: PersonProfile) -> Advice:
    """Turn a weather snapshot into outfit advice for one person."""
    temp_now = snapshot.temp_now
    temp_min = snapshot.temp_min
    temp_max = snapshot.temp_max
    max_precip = snapshot.max_precip_prob
    max_wind = snapshot.max_wind

    # --- Rain --------------------------------------------------------------
    # Rain gear is warranted when any hour in the window is likely wet, or it
    # is already raining now.
    rainy_now = (snapshot.condition_now or "").startswith(
        ("rain", "pouring", "lightning", "snowy-rainy", "hail")
    )
    rain_needed = rainy_now or (
        max_precip is not None and max_precip >= profile.rain_prob_threshold
    )

    # First upcoming hour that crosses the person's rain threshold, so the UI
    # can say *when* to grab the umbrella.
    rain_starts: datetime | None = None
    for hour in snapshot.hours:
        prob = hour.precipitation_probability
        if prob is not None and prob >= profile.rain_prob_threshold:
            rain_starts = hour.datetime
            break

    rain_gear = ""
    if rain_needed:
        windy = max_wind is not None and max_wind >= WIND_UMBRELLA_USELESS
        if windy or not profile.umbrella_over_rainjacket:
            rain_gear = RAIN_JACKET
        else:
            rain_gear = UMBRELLA

    # --- Footwear ----------------------------------------------------------
    # Sandals only if it is comfortably warm right now and staying dry.
    sandals_ok = (
        temp_now is not None
        and temp_now >= profile.sandals_min_temp
        and not rain_needed
    )

    # --- Jacket ------------------------------------------------------------
    # Recommend a jacket if it gets cold enough at any point in the window.
    jacket_needed = temp_min is not None and temp_min <= profile.jacket_max_temp

    recommendation = _build_recommendation(
        sandals_ok=sandals_ok,
        jacket_needed=jacket_needed,
        rain_needed=rain_needed,
        rain_gear=rain_gear,
    )
    message = _build_message(
        snapshot=snapshot,
        sandals_ok=sandals_ok,
        jacket_needed=jacket_needed,
        rain_needed=rain_needed,
        rain_gear=rain_gear,
    )

    return Advice(
        sandals_ok=sandals_ok,
        rain_needed=rain_needed,
        jacket_needed=jacket_needed,
        rain_gear=rain_gear,
        rain_starts=rain_starts,
        temp_now=temp_now,
        temp_min=temp_min,
        temp_max=temp_max,
        max_precip_prob=max_precip,
        max_wind=max_wind,
        recommendation=recommendation,
        message=message,
    )


def _build_recommendation(
    *, sandals_ok: bool, jacket_needed: bool, rain_needed: bool, rain_gear: str
) -> str:
    """Build the short, glanceable summary used as the summary sensor state."""
    parts: list[str] = []
    parts.append("🩴 Sandals" if sandals_ok else "👟 Closed shoes")
    if jacket_needed:
        parts.append("🧥 Jacket")
    if rain_needed:
        parts.append("🧥 Rain jacket" if rain_gear == RAIN_JACKET else "☔ Umbrella")
    return " · ".join(parts)


def _build_message(
    *,
    snapshot: WeatherSnapshot,
    sandals_ok: bool,
    jacket_needed: bool,
    rain_needed: bool,
    rain_gear: str,
) -> str:
    """Build a friendly one-liner suitable for a Lovelace markdown card."""
    temp_now = snapshot.temp_now
    temp_min = snapshot.temp_min
    temp_max = snapshot.temp_max

    if temp_now is None:
        return "No weather data right now."

    sentences: list[str] = []

    # Temperature framing.
    trend = ""
    if temp_min is not None and temp_max is not None:
        if round(temp_max) > round(temp_now):
            trend = f", up to {_fmt_temp(temp_max)} over the next {snapshot.lookahead_hours} h"
        elif round(temp_min) < round(temp_now):
            trend = f", down to {_fmt_temp(temp_min)} over the next {snapshot.lookahead_hours} h"
    sentences.append(f"It's {_fmt_temp(temp_now)} now{trend}.")

    # Footwear + jacket.
    if sandals_ok:
        sentences.append("🩴 Sandals are fine.")
    else:
        sentences.append("👟 Go for closed shoes.")
    if jacket_needed:
        sentences.append("🧥 Bring a jacket.")

    # Rain.
    if rain_needed:
        gear = "a rain jacket" if rain_gear == RAIN_JACKET else "an umbrella"
        sentences.append(f"☔ Rain likely — take {gear}.")
    else:
        sentences.append("☀️ Staying dry.")

    return " ".join(sentences)
