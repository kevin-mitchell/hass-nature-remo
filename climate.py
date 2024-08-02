"""Climate setup for Nature Remo."""

import contextlib
import logging
from typing import Any

from homeassistant.components import climate
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import NatureRemoBase
from .const import DEFAULT_COOL_TEMP, DEFAULT_HEAT_TEMP, DOMAIN
from .coordinator import NatureRemoCoordinator

SUPPORT_FLAGS = (
    climate.ClimateEntityFeature.TARGET_TEMPERATURE
    | climate.ClimateEntityFeature.FAN_MODE
    | climate.ClimateEntityFeature.SWING_MODE
)

_LOGGER = logging.getLogger(__name__)

MODE_HA_TO_REMO = {
    climate.HVACMode.AUTO: "auto",
    climate.HVACMode.FAN_ONLY: "blow",
    climate.HVACMode.COOL: "cool",
    climate.HVACMode.DRY: "dry",
    climate.HVACMode.HEAT: "warm",
    climate.HVACMode.OFF: "power-off",
}

MODE_REMO_TO_HA = {
    "auto": climate.HVACMode.AUTO,
    "blow": climate.HVACMode.FAN_ONLY,
    "cool": climate.HVACMode.COOL,
    "dry": climate.HVACMode.DRY,
    "warm": climate.HVACMode.HEAT,
    "power-off": climate.HVACMode.OFF,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Binary Sensors."""
    # This gets the data update coordinator from hass.data as specified in your __init__.py
    coordinator: NatureRemoCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ].coordinator

    # ----------------------------------------------------------------------------
    # Here we are going to add some lights entities for the lights in our mock data.
    # We have an on/off light and a dimmable light in our mock data, so add each
    # specific class based on the light type.
    # ----------------------------------------------------------------------------
    ac = []

    appliances = coordinator.data["appliances"]

    ac.extend(
        [
            NatureRemoAC(coordinator, appliance, "state")
            for appliance in appliances.values()
            if appliance["type"] == "AC"
        ]
    )

    # Create the AC controls
    async_add_entities(ac)


class NatureRemoAC(NatureRemoBase, climate.ClimateEntity):
    """Implementation of a Nature Remo AC."""

    def __init__(self, coordinator, appliance, config) -> None:
        """Init the AC."""
        super().__init__(coordinator, appliance)
        # self._api = api
        self._default_temp = {
            climate.HVACMode.COOL: DEFAULT_COOL_TEMP,
            climate.HVACMode.HEAT: DEFAULT_HEAT_TEMP,
        }
        self._modes = appliance["aircon"]["range"]["modes"]
        self._hvac_mode = None
        self._current_temperature = None
        self._target_temperature = None
        self._remo_mode = None
        self._fan_mode = None
        self._swing_mode = None
        self._last_target_temperature = {v: None for v in MODE_REMO_TO_HA}
        self._update(appliance["settings"])

    @property
    def supported_features(self) -> climate.const.ClimateEntityFeature:
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._current_temperature

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement which this thermostat uses."""
        return UnitOfTemperature.CELSIUS

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        temp_range = self._current_mode_temp_range()
        if len(temp_range) == 0:
            return 0
        return min(temp_range)

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        temp_range = self._current_mode_temp_range()
        if len(temp_range) == 0:
            return 0
        return max(temp_range)

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        _LOGGER.debug("Current target temperature: %s", self._target_temperature)
        return self._target_temperature

    @property
    def target_temperature_step(self) -> int:
        """Return the supported step of target temperature."""
        temp_range = self._current_mode_temp_range()
        if len(temp_range) >= 2:
            # determine step from the gap of first and second temperature
            step = round(temp_range[1] - temp_range[0], 1)
            if step in [1.0, 0.5]:  # valid steps
                return step
        return 1

    @property
    def hvac_mode(self) -> climate.HVACMode:
        """Return hvac operation ie. heat, cool mode."""
        return self._hvac_mode

    @property
    def hvac_modes(self) -> list[climate.HVACMode]:
        """Return the list of available operation modes."""
        remo_modes = list(self._modes.keys())
        ha_modes = [MODE_REMO_TO_HA[mode] for mode in remo_modes]
        ha_modes.append(climate.HVACMode.OFF)
        return ha_modes

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        return self._fan_mode

    @property
    def fan_modes(self) -> list[str] | None:
        """List of available fan modes."""
        return self._modes[self._remo_mode]["vol"]

    @property
    def swing_mode(self) -> str | None:
        """Return the swing setting."""
        return self._swing_mode

    @property
    def swing_modes(self) -> list[str] | None:
        """List of available swing modes."""
        return self._modes[self._remo_mode]["dir"]

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        return {
            "previous_target_temperature": self._last_target_temperature,
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        target_temp = kwargs.get(ATTR_TEMPERATURE)
        if target_temp is None:
            return
        if target_temp.is_integer():
            # has to cast to whole number otherwise API will return an error
            target_temp = int(target_temp)
        _LOGGER.debug("Set temperature: %d", target_temp)

        response = await self.hass.async_add_executor_job(
            self._coordinator.api.post,
            f"/appliances/{self._appliance_id}/aircon_settings",
            {"temperature": f"{target_temp}"},
        )

        self._update(response)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: climate.const.HVACMode) -> None:
        """Set new target hvac mode."""
        _LOGGER.debug("Set hvac mode: %s", hvac_mode)
        mode = MODE_HA_TO_REMO[hvac_mode]
        if mode == MODE_HA_TO_REMO[climate.HVACMode.OFF]:
            await self._post({"button": mode})
        else:
            data = {"operation_mode": mode}
            if self._last_target_temperature[mode]:
                data["temperature"] = self._last_target_temperature[mode]
            elif self._default_temp.get(hvac_mode):
                data["temperature"] = self._default_temp[hvac_mode]
            await self._post(data)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        _LOGGER.debug("Set fan mode: %s", fan_mode)
        # await self._post({"air_volume": fan_mode})
        response = await self.hass.async_add_executor_job(
            self._coordinator.api.post,
            f"/appliances/{self._appliance_id}/aircon_settings",
            {"air_volume": fan_mode},
        )

        self._update(response)
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""
        _LOGGER.debug("Set swing mode: %s", swing_mode)
        await self._post({"air_direction": swing_mode})

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self._update_callback)
        )

    async def async_update(self) -> None:
        """Update the entity.

        Only used by the generic entity update service.
        """
        await self._coordinator.async_request_refresh()

    def _update(self, ac_settings, device=None):
        # hold this to determin the ac mode while it's turned-off
        self._remo_mode = ac_settings["mode"]
        try:
            self._target_temperature = float(ac_settings["temp"])
            self._last_target_temperature[self._remo_mode] = ac_settings["temp"]
        except KeyError:
            self._target_temperature = None
        except ValueError:
            self._target_temperature = None

        if ac_settings["button"] == MODE_HA_TO_REMO[climate.HVACMode.OFF]:
            self._hvac_mode = climate.HVACMode.OFF
        else:
            self._hvac_mode = MODE_REMO_TO_HA[self._remo_mode]

        self._fan_mode = ac_settings["vol"] or None
        self._swing_mode = ac_settings["dir"] or None

        if device is not None:
            with contextlib.suppress(KeyError):
                self._current_temperature = float(device["newest_events"]["te"]["val"])
                # no op

    @callback
    def _update_callback(self):
        self._update(
            self._coordinator.data["appliances"][self._appliance_id]["settings"],
            self._coordinator.data["devices"][self._device["id"]],
        )
        self.async_write_ha_state()

    async def _post(self, data):
        response = await self.hass.async_add_executor_job(
            self._coordinator.api.post,
            f"/appliances/{self._appliance_id}/aircon_settings",
            data,
        )

        self._update(response)
        self.async_write_ha_state()

    def _current_mode_temp_range(self):
        temp_range = self._modes[self._remo_mode]["temp"]
        return list(map(float, filter(None, temp_range)))
