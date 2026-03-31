import json
import logging
from datetime import datetime
from uuid import uuid4

import requests
from waste_collection_schedule import Collection
from waste_collection_schedule.exceptions import (
    SourceArgumentException,
    SourceArgumentNotFoundWithSuggestions,
    SourceArgumentRequired,
    SourceArgumentRequiredWithSuggestions,
)

TITLE = "Teknik i Väst"
DESCRIPTION = "Waste collection schedule for Teknik i Väst (Arvika, Eda, Årjäng)."
URL = "https://teknikivast.se"
TEST_CASES = {
    "Test": {
        "service_provider": "teknikivast",
        "street_address": "Storgatan 17",
    },
}

HOW_TO_GET_ARGUMENTS_DESCRIPTION = {
    "en": "Enter your street address. On first run a device will be registered and an api_key generated. You can also copy the Enhets-ID from the app settings.",
    "sv": "Ange din gatuadress. Vid första körningen registreras en enhet och en api_key genereras. Du kan också kopiera Enhets-ID från appens inställningar.",
}

COUNTRY = "se"
_LOGGER = logging.getLogger(__name__)

ICON_MAP = {
    "Restavfall": "mdi:trash-can",
    "Matavfall": "mdi:food-apple",
    "Slam": "mdi:water-pump",
    "Fett": "mdi:oil",
    "Tunna 1": "mdi:recycle",
    "Tunna 2": "mdi:recycle",
}

API_URL = "https://teknikivast.avfallsapp.se/api/nova/v1"
AUTH_KEY = "Ef07mdRITQGeiQRId7ao9bmkhIKv2if6ciW17HPWd7a1ae0c"


class Source:
    def __init__(
        self,
        service_provider: str = "teknikivast",
        api_key: str | None = None,
        street_address: str | None = None,
    ):
        if not api_key and not street_address:
            raise SourceArgumentRequired(
                "street_address",
                "Provide a street_address to register, or an existing api_key.",
            )
        self._api_key = api_key
        self._street_address = street_address

    def _headers(self, extra: dict | None = None) -> dict:
        h = {
            "Authorization": f"Bearer {AUTH_KEY}",
            "X-App-Identifier": self._api_key,
            "X-App-Version": "10100",
            "Accept": "application/json",
        }
        if extra:
            h.update(extra)
        return h

    def _register_device(self):
        if not self._street_address:
            raise SourceArgumentRequired(
                "street_address", "Street address required to register device"
            )
        uuid = str(uuid4())
        response = requests.post(
            f"{API_URL}/register",
            json={
                "identifier": uuid,
                "uuid": uuid,
                "platform": "android",
                "version": 10100,
                "os_version": "14",
                "model": "HomeAssistant",
                "test": False,
            },
            headers={
                "Authorization": f"Bearer {AUTH_KEY}",
                "X-App-Identifier": uuid,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        if not response.ok:
            raise SourceArgumentException(
                "api_key", f"Failed to register device: {response.text}"
            )
        _LOGGER.info("Registered device with api_key %s", uuid)
        self._api_key = uuid

    def _register_address(self):
        response = requests.get(
            f"{API_URL}/next-pickup/search",
            params={"address": self._street_address},
            headers=self._headers(),
            timeout=30,
        )
        data = response.json()
        if not data:
            raise SourceArgumentException(
                "street_address",
                f"No addresses found for: {self._street_address}",
            )

        addresses = [a for group in data.values() for a in group]
        _LOGGER.debug("Search returned %d addresses", len(addresses))

        # Try exact match first, otherwise take first result
        match = None
        for a in addresses:
            if a["address"].strip().lower() == self._street_address.strip().lower():
                match = a
                break
        if not match:
            if len(addresses) == 1:
                match = addresses[0]
            else:
                raise SourceArgumentNotFoundWithSuggestions(
                    "street_address",
                    self._street_address,
                    [a["address"].strip() for a in addresses],
                )

        response = requests.post(
            f"{API_URL}/next-pickup/set-status",
            json={
                "plant_id": match["plant_number"],
                "address_enabled": True,
                "notification_enabled": False,
            },
            headers=self._headers({"Content-Type": "application/json"}),
            timeout=30,
        )
        response.raise_for_status()
        _LOGGER.info("Registered address %s", match["address"])

    def fetch(self) -> list[Collection]:
        if not self._api_key:
            self._register_device()
            self._register_address()
            raise SourceArgumentRequiredWithSuggestions(
                "api_key",
                "Select the generated api_key",
                [self._api_key],
            )

        response = requests.get(
            f"{API_URL}/next-pickup/list",
            headers=self._headers(),
            timeout=30,
        )
        data = response.json()
        multi = len(data) > 1
        entries = []
        for entry in data:
            address = entry.get("address", "")
            for b in entry.get("bins", []):
                pickup_date = b.get("pickup_date")
                if not pickup_date or pickup_date == "0000-00-00":
                    continue
                waste_type = b.get("type", "Unknown")
                icon = ICON_MAP.get(waste_type, "mdi:trash-can")
                if multi:
                    waste_type = f"{address} {waste_type}"
                entries.append(
                    Collection(
                        date=datetime.strptime(pickup_date, "%Y-%m-%d").date(),
                        t=waste_type,
                        icon=icon,
                    )
                )

        return entries
