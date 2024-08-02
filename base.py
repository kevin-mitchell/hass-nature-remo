"""Base entity which all other entity platform classes can inherit.

As all entity types have a common set of properties, you can
create a base entity like this and inherit it in all your entity platforms.

This just makes your code more efficient and is totally optional.

See each entity platform (ie sensor.py, switch.py) for how this is inheritted
and what additional properties and methods you need to add for each entity type.

"""

import logging
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NatureRemoCoordinator

_LOGGER = logging.getLogger(__name__)


class NatureRemoBaseEntity(CoordinatorEntity):
    """Base Entity Class.

    This inherits a CoordinatorEntity class to register your entites to be updated
    by your DataUpdateCoordinator when async_update_data is called, either on the scheduled
    interval or by forcing an update.
    """

    coordinator: NatureRemoCoordinator

    # ----------------------------------------------------------------------------
    # Using attr_has_entity_name = True causes HA to name your entities with the
    # device name and entity name.  Ie if your name property of your entity is
    # Voltage and this entity belongs to a device, Lounge Socket, this will name
    # your entity to be sensor.lounge_socket_voltage
    #
    # It is highly recommended (by me) to use this to give a good name structure
    # to your entities.  However, totally optional.
    # ----------------------------------------------------------------------------
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: NatureRemoCoordinator, device: dict[str, Any], parameter: str
    ) -> None:
        """Initialise entity."""
        super().__init__(coordinator)
        self.device = device
        self.device_id = device["device_id"]
        self.parameter = parameter

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        self.device = self.coordinator.get_device(self.device_id)
        _LOGGER.debug(
            "Updating device: %s, %s",
            self.device_id,
            self.coordinator.get_device_parameter(self.device_id, "device_name"),
        )
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""

        # ----------------------------------------------------------------------------
        # Identifiers are what group entities into the same device.
        # If your device is created elsewhere, you can just specify the indentifiers
        # parameter to link an entity to a device.
        # If your device connects via another device, add via_device parameter with
        # the indentifiers of that device.
        #
        # Device identifiers should be unique, so use your integration name (DOMAIN)
        # and a device uuid, mac address or some other unique attribute.
        # ----------------------------------------------------------------------------
        return DeviceInfo(
            name=self.coordinator.get_device_parameter(self.device_id, "device_name"),
            manufacturer="ACME Manufacturer",
            model=str(
                self.coordinator.get_device_parameter(self.device_id, "device_type")
            )
            .replace("_", " ")
            .title(),
            sw_version=self.coordinator.get_device_parameter(
                self.device_id, "software_version"
            ),
            identifiers={
                (
                    DOMAIN,
                    self.coordinator.get_device_parameter(self.device_id, "device_uid"),
                )
            },
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self.parameter.replace("_", " ").title()

    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return False

    @property
    def unique_id(self) -> str:
        """Return unique id."""

        # ----------------------------------------------------------------------------
        # All entities must have a unique id across your whole Home Assistant server -
        # and that also goes for anyone using your integration who may have many other
        # integrations loaded.
        #
        # Think carefully what you want this to be as changing it later will cause HA
        # to create new entities.
        #
        # It is recommended to have your integration name (DOMAIN), some unique id
        # from your device such as a UUID, MAC address etc (not IP address) and then
        # something unique to your entity (like name - as this would be unique on a
        # device)
        #
        # If in your situation you have some hub that connects to devices which then
        # you want to create multiple sensors for each device, you would do something
        # like.
        #
        # f"{DOMAIN}-{HUB_MAC_ADDRESS}-{DEVICE_UID}-{ENTITY_NAME}""
        #
        # This is even more important if your integration supports multiple instances.
        # ----------------------------------------------------------------------------
        return f"{DOMAIN}-{self.coordinator.get_device_parameter(self.device_id, "device_uid")}-{self.parameter}"


class NatureRemoBase(Entity):
    """Nature Remo entity base class."""

    def __init__(self, coordinator, appliance) -> None:
        """Init the thing."""
        self._coordinator = coordinator
        self._name = f"Nature Remo {appliance['nickname']}"
        self._appliance_id = appliance["id"]
        self._device = appliance["device"]

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._appliance_id

    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return False

    @property
    def device_info(self):
        """Return the device info for the sensor."""
        # Since device registration requires Config Entries, this dosen't work for now
        return {
            "identifiers": {(DOMAIN, self._device["id"])},
            "name": self._device["name"],
            "manufacturer": "Nature Remo",
            "model": self._device["serial_number"],
            "sw_version": self._device["firmware_version"],
        }
