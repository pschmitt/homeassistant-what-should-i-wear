"""Shared entity helpers for the What Should I Wear? integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .advisor import Advice, PersonProfile, evaluate
from .const import (
    CONF_JACKET_MAX_TEMP,
    CONF_RAIN_PROB_THRESHOLD,
    CONF_SANDALS_MIN_TEMP,
    CONF_UMBRELLA_OVER_RAINJACKET,
    DEFAULT_JACKET_MAX_TEMP,
    DEFAULT_RAIN_PROB_THRESHOLD,
    DEFAULT_SANDALS_MIN_TEMP,
    DEFAULT_UMBRELLA_OVER_RAINJACKET,
    DOMAIN,
)
from .coordinator import WswCoordinator


def profile_from_subentry(subentry: ConfigSubentry) -> PersonProfile:
    """Build a :class:`PersonProfile` from a person config subentry."""
    data = subentry.data
    return PersonProfile(
        name=subentry.title,
        sandals_min_temp=float(
            data.get(CONF_SANDALS_MIN_TEMP, DEFAULT_SANDALS_MIN_TEMP)
        ),
        jacket_max_temp=float(
            data.get(CONF_JACKET_MAX_TEMP, DEFAULT_JACKET_MAX_TEMP)
        ),
        rain_prob_threshold=float(
            data.get(CONF_RAIN_PROB_THRESHOLD, DEFAULT_RAIN_PROB_THRESHOLD)
        ),
        umbrella_over_rainjacket=bool(
            data.get(
                CONF_UMBRELLA_OVER_RAINJACKET, DEFAULT_UMBRELLA_OVER_RAINJACKET
            )
        ),
    )


class WswPersonEntity(CoordinatorEntity[WswCoordinator]):
    """Base entity bound to a person's device (one config subentry)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WswCoordinator,
        subentry_id: str,
        profile: PersonProfile,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._subentry_id = subentry_id
        self._profile = profile
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, subentry_id)},
            name=profile.name,
            manufacturer="pschmitt",
            model="Outfit advisor",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def advice(self) -> Advice | None:
        """Return the current advice for this person, or None when no data."""
        snapshot = self.coordinator.data
        if snapshot is None:
            return None
        return evaluate(snapshot, self._profile)

    @property
    def available(self) -> bool:
        """Available only once we have a usable weather snapshot."""
        snapshot = self.coordinator.data
        return (
            super().available
            and snapshot is not None
            and snapshot.temp_now is not None
        )
