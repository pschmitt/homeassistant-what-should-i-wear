"""Sensor platform for the What Should I Wear? integration.

One glanceable summary sensor per person whose state is a short outfit
recommendation (e.g. "🩴 Sandals · ☔ Umbrella"), with a friendly message and
the driving weather numbers as attributes for dashboards and automations.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WswConfigEntry
from .const import (
    ATTR_LOOKAHEAD_HOURS,
    ATTR_MAX_PRECIP_PROB,
    ATTR_MAX_WIND,
    ATTR_MESSAGE,
    ATTR_PRIMARY_INFO,
    ATTR_RAIN_GEAR,
    ATTR_RAIN_STARTS,
    ATTR_RECOMMENDATION,
    ATTR_SECONDARY_INFO,
    ATTR_TEMP_MAX,
    ATTR_TEMP_MIN,
    ATTR_TEMP_NOW,
    SUBENTRY_TYPE_PERSON,
)
from .coordinator import WswCoordinator
from .entity import WswPersonEntity, profile_from_subentry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WswConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the per-person summary sensors."""
    coordinator = entry.runtime_data

    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_PERSON:
            continue
        profile = profile_from_subentry(subentry)
        async_add_entities(
            [SummarySensor(coordinator, subentry_id, profile)],
            config_subentry_id=subentry_id,
        )


class SummarySensor(WswPersonEntity, SensorEntity):
    """A short, human-readable 'what to wear' recommendation."""

    _attr_translation_key = "summary"
    _attr_name = "What to wear"
    _attr_icon = "mdi:hanger"

    def __init__(self, coordinator: WswCoordinator, subentry_id, profile) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, subentry_id, profile)
        self._attr_unique_id = f"{subentry_id}_summary"

    @property
    def native_value(self) -> str | None:
        """Return the short recommendation string."""
        advice = self.advice
        return advice.recommendation if advice else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return the full advice context for dashboards and automations."""
        advice = self.advice
        if advice is None:
            return {}
        return {
            ATTR_RECOMMENDATION: advice.recommendation,
            ATTR_MESSAGE: advice.message,
            ATTR_TEMP_NOW: advice.temp_now,
            ATTR_TEMP_MIN: advice.temp_min,
            ATTR_TEMP_MAX: advice.temp_max,
            ATTR_MAX_PRECIP_PROB: advice.max_precip_prob,
            ATTR_MAX_WIND: advice.max_wind,
            ATTR_RAIN_GEAR: advice.rain_gear or None,
            ATTR_RAIN_STARTS: (
                advice.rain_starts.isoformat() if advice.rain_starts else None
            ),
            ATTR_LOOKAHEAD_HOURS: self.coordinator.lookahead_hours,
            # Convenience aliases for markdown / button cards.
            ATTR_PRIMARY_INFO: advice.recommendation,
            ATTR_SECONDARY_INFO: advice.message,
        }
