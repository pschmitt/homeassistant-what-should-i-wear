"""Constants for the What Should I Wear? integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "what_should_i_wear"
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

# ---------------------------------------------------------------------------
# Main config entry (the "hub"): which weather entity to read and how far
# ahead the advice should look. These are shared by every person.
# ---------------------------------------------------------------------------
CONF_WEATHER_ENTITY = "weather_entity"
CONF_LOOKAHEAD_HOURS = "lookahead_hours"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_WEATHER_ENTITY = "weather.openweathermap"
DEFAULT_LOOKAHEAD_HOURS = 6
MIN_LOOKAHEAD_HOURS = 1
MAX_LOOKAHEAD_HOURS = 24
DEFAULT_SCAN_INTERVAL = 900  # 15 minutes
MIN_SCAN_INTERVAL = 60

# ---------------------------------------------------------------------------
# Per-person profile (one config subentry per person). Only the comfort
# thresholds differ between people; the decision logic itself is shared.
# ---------------------------------------------------------------------------
SUBENTRY_TYPE_PERSON = "person"

CONF_SANDALS_MIN_TEMP = "sandals_min_temp"
CONF_JACKET_MAX_TEMP = "jacket_max_temp"
CONF_RAIN_PROB_THRESHOLD = "rain_prob_threshold"
CONF_UMBRELLA_OVER_RAINJACKET = "umbrella_over_rainjacket"

# Sensible defaults for a Central-European wardrobe; tweak per person in the UI.
DEFAULT_SANDALS_MIN_TEMP = 22.0  # °C: warm enough to bare your toes
DEFAULT_JACKET_MAX_TEMP = 14.0  # °C: cold enough to want a jacket
DEFAULT_RAIN_PROB_THRESHOLD = 40.0  # %: precip probability that warrants rain gear
DEFAULT_UMBRELLA_OVER_RAINJACKET = True

# Above this wind speed an umbrella is useless, so rain gear advice flips to a
# rain jacket regardless of the person's umbrella preference.
WIND_UMBRELLA_USELESS = 30.0  # km/h

# ---------------------------------------------------------------------------
# Items advised on, exposed as one binary sensor each per person.
# ---------------------------------------------------------------------------
ITEM_SANDALS = "sandals"
ITEM_RAIN = "rain"
ITEM_JACKET = "jacket"

# ---------------------------------------------------------------------------
# Entity state attributes.
# ---------------------------------------------------------------------------
ATTR_MESSAGE = "message"
ATTR_RECOMMENDATION = "recommendation"
ATTR_TEMP_NOW = "temperature_now"
ATTR_TEMP_MIN = "temperature_min"
ATTR_TEMP_MAX = "temperature_max"
ATTR_MAX_PRECIP_PROB = "max_precipitation_probability"
ATTR_MAX_WIND = "max_wind_speed"
ATTR_RAIN_GEAR = "rain_gear"
ATTR_RAIN_STARTS = "rain_starts"
ATTR_RAIN_STARTS_IN = "rain_starts_in"
ATTR_LOOKAHEAD_HOURS = "lookahead_hours"
ATTR_PRIMARY_INFO = "primary_info"
ATTR_SECONDARY_INFO = "secondary_info"
