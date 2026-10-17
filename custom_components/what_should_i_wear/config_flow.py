"""Config flow for the What Should I Wear? integration.

The main config entry is the shared "hub": which weather entity to read and
how far ahead to look. Each person is a config subentry carrying their own
comfort thresholds, so people can be added, edited, and removed from the UI.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import (
    CONF_JACKET_MAX_TEMP,
    CONF_LOOKAHEAD_HOURS,
    CONF_RAIN_PROB_THRESHOLD,
    CONF_SANDALS_MIN_TEMP,
    CONF_SCAN_INTERVAL,
    CONF_TEMPERATURE_ENTITY,
    CONF_UMBRELLA_OVER_RAINJACKET,
    CONF_WEATHER_ENTITY,
    DEFAULT_JACKET_MAX_TEMP,
    DEFAULT_LOOKAHEAD_HOURS,
    DEFAULT_RAIN_PROB_THRESHOLD,
    DEFAULT_SANDALS_MIN_TEMP,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UMBRELLA_OVER_RAINJACKET,
    DEFAULT_WEATHER_ENTITY,
    DOMAIN,
    MAX_LOOKAHEAD_HOURS,
    MIN_LOOKAHEAD_HOURS,
    MIN_SCAN_INTERVAL,
    SUBENTRY_TYPE_PERSON,
)

TITLE = "What Should I Wear?"


def _hub_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Schema for the shared weather/lookahead settings."""
    return vol.Schema(
        {
            vol.Required(
                CONF_WEATHER_ENTITY,
                default=defaults.get(CONF_WEATHER_ENTITY, DEFAULT_WEATHER_ENTITY),
            ): EntitySelector(EntitySelectorConfig(domain="weather")),
            vol.Optional(
                CONF_TEMPERATURE_ENTITY,
                description={"suggested_value": defaults.get(CONF_TEMPERATURE_ENTITY) or None},
            ): EntitySelector(EntitySelectorConfig(domain="sensor", device_class="temperature")),
            vol.Required(
                CONF_LOOKAHEAD_HOURS,
                default=defaults.get(CONF_LOOKAHEAD_HOURS, DEFAULT_LOOKAHEAD_HOURS),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_LOOKAHEAD_HOURS,
                    max=MAX_LOOKAHEAD_HOURS,
                    step=1,
                    mode=NumberSelectorMode.SLIDER,
                    unit_of_measurement="h",
                )
            ),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
        }
    )


def _person_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Schema for a person's comfort thresholds."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): TextSelector(),
            vol.Required(
                CONF_SANDALS_MIN_TEMP,
                default=defaults.get(CONF_SANDALS_MIN_TEMP, DEFAULT_SANDALS_MIN_TEMP),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=40,
                    step=0.5,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="°C",
                )
            ),
            vol.Required(
                CONF_JACKET_MAX_TEMP,
                default=defaults.get(CONF_JACKET_MAX_TEMP, DEFAULT_JACKET_MAX_TEMP),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=-10,
                    max=30,
                    step=0.5,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="°C",
                )
            ),
            vol.Required(
                CONF_RAIN_PROB_THRESHOLD,
                default=defaults.get(CONF_RAIN_PROB_THRESHOLD, DEFAULT_RAIN_PROB_THRESHOLD),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=5,
                    mode=NumberSelectorMode.SLIDER,
                    unit_of_measurement="%",
                )
            ),
            vol.Required(
                CONF_UMBRELLA_OVER_RAINJACKET,
                default=defaults.get(
                    CONF_UMBRELLA_OVER_RAINJACKET,
                    DEFAULT_UMBRELLA_OVER_RAINJACKET,
                ),
            ): BooleanSelector(),
        }
    )


class WswConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for What Should I Wear?."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> WswOptionsFlow:
        """Return the options flow."""
        return WswOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Person profiles are managed as subentries."""
        return {SUBENTRY_TYPE_PERSON: PersonSubentryFlowHandler}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the single-instance setup step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title=TITLE,
                data={},
                options=_hub_options(user_input),
            )

        return self.async_show_form(step_id="user", data_schema=_hub_schema({}))


class WswOptionsFlow(OptionsFlow):
    """Handle the shared options for What Should I Wear?."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the weather/lookahead settings."""
        if user_input is not None:
            return self.async_create_entry(title="", data=_hub_options(user_input))

        return self.async_show_form(
            step_id="init",
            data_schema=_hub_schema(dict(self.config_entry.options)),
        )


class PersonSubentryFlowHandler(ConfigSubentryFlow):
    """Add or reconfigure a person profile."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Add a new person."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=_normalize_person(user_input),
            )

        return self.async_show_form(step_id="user", data_schema=_person_schema({}))

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit an existing person."""
        subentry = self._get_reconfigure_subentry()
        if user_input is not None:
            return self.async_update_and_abort(
                self._get_entry(),
                subentry,
                title=user_input[CONF_NAME],
                data=_normalize_person(user_input),
            )

        defaults = {CONF_NAME: subentry.title, **subentry.data}
        return self.async_show_form(step_id="reconfigure", data_schema=_person_schema(defaults))


def _hub_options(user_input: dict[str, Any]) -> dict[str, Any]:
    """Coerce the hub form into clean, typed entry options."""
    return {
        CONF_WEATHER_ENTITY: user_input[CONF_WEATHER_ENTITY],
        CONF_TEMPERATURE_ENTITY: user_input.get(CONF_TEMPERATURE_ENTITY) or "",
        CONF_LOOKAHEAD_HOURS: int(user_input[CONF_LOOKAHEAD_HOURS]),
        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
    }


def _normalize_person(user_input: dict[str, Any]) -> dict[str, Any]:
    """Coerce a person form submission into a clean, typed subentry payload."""
    return {
        CONF_NAME: user_input[CONF_NAME],
        CONF_SANDALS_MIN_TEMP: float(user_input[CONF_SANDALS_MIN_TEMP]),
        CONF_JACKET_MAX_TEMP: float(user_input[CONF_JACKET_MAX_TEMP]),
        CONF_RAIN_PROB_THRESHOLD: float(user_input[CONF_RAIN_PROB_THRESHOLD]),
        CONF_UMBRELLA_OVER_RAINJACKET: bool(user_input[CONF_UMBRELLA_OVER_RAINJACKET]),
    }
