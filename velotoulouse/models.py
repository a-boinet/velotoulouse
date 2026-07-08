from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Station:
    id: str
    name: str
    latitude: float
    longitude: float
    address: str
    rental_methods: list
    capacity: int
    bikes_available: int
    bikes_disabled: int
    docks_available: int
    docks_disabled: int
    mechanical_bikes: int
    electrical_bikes: int
    is_renting: bool
    is_returning: bool
    last_reported: datetime
    last_updated: datetime

    _client: "VeloToulouseClient"  # NOQA

    def refresh_status(self):
        self._client.refresh_station(self)
