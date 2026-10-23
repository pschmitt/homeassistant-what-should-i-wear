"""The What Should I Wear? integration.

Reads an hourly weather forecast and turns it into per-person outfit advice:
whether sandals are fine, whether to take a jacket, and whether rain gear
(umbrella or rain jacket) is needed now and over the next few hours. Each
person is a config subentry with their own comfort thresholds.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import WswCoordinator

type WswConfigEntry = ConfigEntry[WswCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: WswConfigEntry) -> bool:
    """Set up What Should I Wear? from a config entry."""
    coordinator = WswCoordinator(hass, entry)
    coordinator.async_setup_listeners()

    entry.runtime_data = coordinator

    if coordinator.data is None:
        coordinator.last_update_success = False
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))

    entry.async_create_background_task(
        hass, coordinator.async_refresh(), "what_should_i_wear_first_refresh"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WswConfigEntry) -> bool:
    """Unload a What Should I Wear? config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_on_update(hass: HomeAssistant, entry: WswConfigEntry) -> None:
    """Reload when options or person subentries change.

    Persons are config subentries; adding, editing, or removing one changes the
    set of entities, so the simplest correct response is a full reload.
    """
    await hass.config_entries.async_reload(entry.entry_id)
