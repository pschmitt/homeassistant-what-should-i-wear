"""Binary sensor platform for the What Should I Wear? integration.

One device per person (a config subentry), each exposing three advisory
binary sensors: sandals OK, rain gear needed, and jacket needed.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WswConfigEntry
from .advisor import RAIN_JACKET
from .const import (
    ATTR_MAX_PRECIP_PROB,
    ATTR_MAX_WIND,
    ATTR_MESSAGE,
    ATTR_RAIN_GEAR,
    ATTR_RAIN_STARTS,
    ATTR_TEMP_MIN,
    ATTR_TEMP_NOW,
    ITEM_JACKET,
    ITEM_RAIN,
    ITEM_SANDALS,
    SUBENTRY_TYPE_PERSON,
)
from .coordinator import WswCoordinator
from .entity import WswPersonEntity, profile_from_subentry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WswConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the per-person advisory binary sensors."""
    coordinator = entry.runtime_data

    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_PERSON:
            continue
        profile = profile_from_subentry(subentry)
        async_add_entities(
            [
                SandalsBinarySensor(coordinator, subentry_id, profile),
                RainBinarySensor(coordinator, subentry_id, profile),
                JacketBinarySensor(coordinator, subentry_id, profile),
            ],
            config_subentry_id=subentry_id,
        )


class SandalsBinarySensor(WswPersonEntity, BinarySensorEntity):
    """On when it is warm and dry enough for sandals."""

    _attr_translation_key = ITEM_SANDALS

    def __init__(self, coordinator: WswCoordinator, subentry_id, profile) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, subentry_id, profile)
        self._attr_unique_id = f"{subentry_id}_{ITEM_SANDALS}"

    @property
    def is_on(self) -> bool | None:
        """Return True when sandals are a good call."""
        advice = self.advice
        return advice.sandals_ok if advice else None

    @property
    def icon(self) -> str:
        """Return a foot/shoe icon reflecting the verdict."""
        return "mdi:shoe-sneaker" if self.is_on is False else "mdi:shoe-formal"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return the driving numbers and message."""
        advice = self.advice
        if advice is None:
            return {}
        return {
            ATTR_TEMP_NOW: advice.temp_now,
            ATTR_MAX_PRECIP_PROB: advice.max_precip_prob,
            ATTR_MESSAGE: advice.message,
        }


class RainBinarySensor(WswPersonEntity, BinarySensorEntity):
    """On when rain gear (umbrella or rain jacket) is warranted."""

    _attr_translation_key = ITEM_RAIN

    def __init__(self, coordinator: WswCoordinator, subentry_id, profile) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, subentry_id, profile)
        self._attr_unique_id = f"{subentry_id}_{ITEM_RAIN}"

    @property
    def is_on(self) -> bool | None:
        """Return True when rain protection is recommended."""
        advice = self.advice
        return advice.rain_needed if advice else None

    @property
    def icon(self) -> str:
        """Return an umbrella/rain-jacket icon reflecting the recommendation."""
        advice = self.advice
        if advice is None or not advice.rain_needed:
            return "mdi:weather-sunny"
        return "mdi:coat-rack" if advice.rain_gear == RAIN_JACKET else "mdi:umbrella"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return the rain details (gear, probability, when it starts)."""
        advice = self.advice
        if advice is None:
            return {}
        return {
            ATTR_RAIN_GEAR: advice.rain_gear or None,
            ATTR_MAX_PRECIP_PROB: advice.max_precip_prob,
            ATTR_MAX_WIND: advice.max_wind,
            ATTR_RAIN_STARTS: (
                advice.rain_starts.isoformat() if advice.rain_starts else None
            ),
            ATTR_MESSAGE: advice.message,
        }


class JacketBinarySensor(WswPersonEntity, BinarySensorEntity):
    """On when it gets cold enough to want a jacket within the window."""

    _attr_translation_key = ITEM_JACKET

    def __init__(self, coordinator: WswCoordinator, subentry_id, profile) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, subentry_id, profile)
        self._attr_unique_id = f"{subentry_id}_{ITEM_JACKET}"

    @property
    def is_on(self) -> bool | None:
        """Return True when a jacket is recommended."""
        advice = self.advice
        return advice.jacket_needed if advice else None

    @property
    def icon(self) -> str:
        """Return a coat icon reflecting the verdict."""
        return "mdi:coat-rack" if self.is_on else "mdi:tshirt-crew"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return the temperatures that drove the verdict."""
        advice = self.advice
        if advice is None:
            return {}
        return {
            ATTR_TEMP_NOW: advice.temp_now,
            ATTR_TEMP_MIN: advice.temp_min,
            ATTR_MESSAGE: advice.message,
        }
