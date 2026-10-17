"""Coordinator for the What Should I Wear? integration.

Fetches the hourly forecast from the configured weather entity, trims it to
the lookahead window, and exposes a person-independent
:class:`WeatherSnapshot`. A short poll keeps the snapshot fresh; a state
listener on the weather entity makes updates effectively immediate.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .advisor import ForecastHour, WeatherSnapshot
from .const import (
    CONF_LOOKAHEAD_HOURS,
    CONF_SCAN_INTERVAL,
    CONF_TEMPERATURE_ENTITY,
    CONF_WEATHER_ENTITY,
    DEFAULT_LOOKAHEAD_HOURS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TEMPERATURE_ENTITY,
    DEFAULT_WEATHER_ENTITY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class WswCoordinator(DataUpdateCoordinator[WeatherSnapshot]):
    """Keep a current weather snapshot for the outfit advice to read."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(
                seconds=config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    @property
    def weather_entity(self) -> str:
        """Return the configured weather entity id."""
        return self.config_entry.options.get(CONF_WEATHER_ENTITY, DEFAULT_WEATHER_ENTITY)

    @property
    def temperature_entity(self) -> str:
        """Return the optional current-temperature sensor (empty = use weather)."""
        return self.config_entry.options.get(CONF_TEMPERATURE_ENTITY, DEFAULT_TEMPERATURE_ENTITY)

    @property
    def lookahead_hours(self) -> int:
        """Return how many hours ahead the advice considers."""
        return int(self.config_entry.options.get(CONF_LOOKAHEAD_HOURS, DEFAULT_LOOKAHEAD_HOURS))

    @callback
    def async_setup_listeners(self) -> None:
        """Refresh promptly whenever the weather entity changes."""

        @callback
        def _on_weather_change(_event: Event) -> None:
            self.config_entry.async_create_task(
                self.hass,
                self.async_request_refresh(),
                "wsw_weather_refresh",
            )

        tracked = [self.weather_entity]
        if self.temperature_entity:
            tracked.append(self.temperature_entity)
        self.config_entry.async_on_unload(
            async_track_state_change_event(self.hass, tracked, _on_weather_change)
        )

    async def _async_update_data(self) -> WeatherSnapshot:
        """Fetch the forecast and build a trimmed snapshot."""
        weather_entity = self.weather_entity
        state = self.hass.states.get(weather_entity)
        if state is None or state.state in ("unavailable", "unknown"):
            # Weather entities blip unavailable routinely (provider refresh,
            # startup ordering) — keep the last snapshot instead of erroring.
            if self.data is not None:
                _LOGGER.debug(
                    "Weather entity %s is unavailable; keeping last snapshot",
                    weather_entity,
                )
                return self.data
            raise UpdateFailed(f"Weather entity {weather_entity} is unavailable")

        condition_now = state.state

        # Current temperature: prefer the dedicated sensor (weather "now" values
        # are often wrong/laggy); fall back to the weather entity's attribute.
        temp_now = _as_float(state.attributes.get("temperature"))
        if self.temperature_entity:
            temp_state = self.hass.states.get(self.temperature_entity)
            if temp_state is not None and temp_state.state not in (
                "unavailable",
                "unknown",
            ):
                override = _as_float(temp_state.state)
                if override is not None:
                    temp_now = override

        try:
            response = await self.hass.services.async_call(
                "weather",
                "get_forecasts",
                {"type": "hourly", "entity_id": weather_entity},
                blocking=True,
                return_response=True,
            )
        except Exception as err:  # noqa: BLE001 - surface any service failure as UpdateFailed
            raise UpdateFailed(
                f"Could not get hourly forecast from {weather_entity}: {err}"
            ) from err

        forecast = (response or {}).get(weather_entity, {}).get("forecast", [])
        hours = self._trim_forecast(forecast)

        return WeatherSnapshot(
            temp_now=temp_now,
            condition_now=condition_now,
            hours=hours,
            lookahead_hours=self.lookahead_hours,
        )

    def _trim_forecast(self, forecast: list[dict]) -> list[ForecastHour]:
        """Keep only future forecast points within the lookahead window."""
        now = dt_util.utcnow()
        # Include the current hour's point (timestamped at the top of the
        # hour) so rain falling right now still influences the advice.
        start = now.replace(minute=0, second=0, microsecond=0)
        cutoff = now + timedelta(hours=self.lookahead_hours)
        hours: list[ForecastHour] = []
        for item in forecast:
            raw_dt = item.get("datetime")
            when = dt_util.parse_datetime(raw_dt) if raw_dt else None
            if when is None:
                continue
            when = dt_util.as_utc(when)
            if when < start or when > cutoff:
                continue
            hours.append(
                ForecastHour(
                    datetime=when,
                    temperature=_as_float(item.get("temperature")),
                    precipitation_probability=_as_float(item.get("precipitation_probability")),
                    wind_speed=_as_float(item.get("wind_speed")),
                    condition=item.get("condition"),
                )
            )
        hours.sort(key=lambda hour: hour.datetime)
        return hours


def _as_float(value: object) -> float | None:
    """Coerce a forecast value to float, tolerating None and bad data."""
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
