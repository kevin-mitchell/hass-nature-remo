"""Constants for the Nature Remo integration."""

DOMAIN = "nature_remo"
HOST = "https://api.nature.global/1/"
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 10

DEFAULT_COOL_TEMP = 28
DEFAULT_HEAT_TEMP = 20
# TODO: this was a config property we're not using
CONF_COOL_TEMP = "cool_temperature"
CONF_HEAT_TEMP = "heat_temperature"


RENAME_DEVICE_SERVICE_NAME = "rename_device_service"
RESPONSE_SERVICE_NAME = "response_service"
