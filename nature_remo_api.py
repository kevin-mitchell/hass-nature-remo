"""A simple Nature Remo API Client."""

import logging

import requests

_LOGGER = logging.getLogger(__name__)


class NatureRemoAPI:
    """Nature Remo API client."""

    def __init__(self, host, access_token) -> None:
        """Init API client."""
        self._access_token = access_token
        self._host = host

    def authenticate_check(self) -> bool:
        """Make basic check for authorization."""
        _LOGGER.debug("Trying to fetch appliance and device list from API")
        headers = {"Authorization": f"Bearer {self._access_token}"}
        response = requests.get(f"{self._host}/appliances", headers=headers, timeout=10)

        if response.status_code != 200:
            return False

        response_json = response.json()

        appliances = {x["id"]: x for x in response_json}
        return True

    def get(self):
        """Get appliance and device list."""
        _LOGGER.debug("Trying to fetch appliance and device list from API")
        headers = {"Authorization": f"Bearer {self._access_token}"}
        response = requests.get(f"{self._host}/appliances", headers=headers, timeout=10)
        appliances = {x["id"]: x for x in response.json()}

        response = requests.get(f"{self._host}/devices", headers=headers, timeout=10)
        devices = {x["id"]: x for x in response.json()}
        return {"appliances": appliances, "devices": devices}

    def post(self, path, data):
        """Post any request."""
        _LOGGER.debug("Trying to request post:%s, data:%s", path, data)
        headers = {"Authorization": f"Bearer {self._access_token}"}
        response = requests.post(
            f"{self._host}{path}", data=data, headers=headers, timeout=10
        )
        return response.json()


class APIAuthError(Exception):
    """Exception class for auth error."""


class APIConnectionError(Exception):
    """Exception class for connection error."""
