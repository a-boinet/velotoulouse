from dataclasses import dataclass
from datetime import datetime
from functools import cached_property

from . import DEFAULT_STATION_STATUS_TTL
from .utils import get_data_with_cache


@dataclass
class Station:
    _station_information: StationInformation
    _station_status: StationStatus

    def __post_init__(self):
        if self._station_information.id != self._station_status.id:
            raise ValueError(
                f"Station ID don't match "
                f"({self._station_information.id} != {self._station_status.id})"
            )

    @cached_property
    def id(self):
        return self._station_information.id

    @cached_property
    def name(self):
        return self._station_information.name

    @cached_property
    def latitude(self):
        return self._station_information.latitude

    @cached_property
    def longitude(self):
        return self._station_information.longitude

    @cached_property
    def address(self):
        return self._station_information.address

    @cached_property
    def rental_methods(self):
        return self._station_information.rental_methods

    @property
    def capacity(self):
        return self._station_information.capacity

    @property
    def bikes_available(self):
        return self._station_status.bikes_available

    @property
    def bikes_disabled(self):
        return self._station_status.bikes_disabled

    @property
    def docks_available(self):
        return self._station_status.docks_available

    @property
    def docks_disabled(self):
        return self._station_status.docks_disabled

    @property
    def mechanical_bikes(self):
        return self._station_status.mechanical_bikes

    @property
    def electrical_bikes(self):
        return self._station_status.electrical_bikes

    @property
    def is_renting(self):
        return self._station_status.is_renting

    @property
    def is_returning(self):
        return self._station_status.is_returning

    @property
    def last_reported(self):
        return self._station_status.last_reported


"""
d = {
    "station_id": "1",
    "name": [
        {
            "text": "POIDS DE L'HUILE",
            "language": "fr"
        },
        {
            "text": "POIDS DE L'HUILE",
            "language": "en"
        },
        {
            "text": "POIDS DE L'HUILE",
            "language": "es"
        }
    ],
    "lat": 43.60419,
    "lon": 1.445475,
    "address": "12 RUE DU POIDS DE L'HUILE",
    "capacity": 19
}
"""


def parse_station_information_dict(d: dict, language: str) -> dict:
    _id = d["station_id"]
    for _name_dict in d["name"]:
        if _name_dict["language"] == language:
            _name = _name_dict["text"]
            break
    else:
        _name = d["name"][0]["text"]  # Fallback
    _latitude = float(d["lat"])
    _longitude = float(d["lon"])
    _address = d["address"]
    _capacity = int(d["capacity"])
    rental_methods = d.get("rental_methods", [])
    return {
        "id": _id,
        "name": _name,
        "latitude": _latitude,
        "longitude": _longitude,
        "address": _address,
        "capacity": _capacity,
        "rental_methods": rental_methods,
        "language": language,
    }


@dataclass
class StationInformation:
    id: str
    name: str
    latitude: float
    longitude: float
    address: str
    capacity: int
    rental_methods: list
    _language: str

    @classmethod
    def from_dict(cls, d, language: str="fr"):
        parsed = parse_station_information_dict(d, language)
        return cls(
            parsed["id"],
            parsed["name"],
            parsed["latitude"],
            parsed["longitude"],
            parsed["address"],
            parsed["capacity"],
            parsed["rental_methods"],
            language
        )

    def refresh(self, d: dict):
        parsed = parse_station_information_dict(d, self._language)
        self.id = parsed["id"]
        self.name = parsed["name"]
        self.latitude = parsed["latitude"]
        self.longitude = parsed["longitude"]
        self.address = parsed["address"]
        self.capacity = parsed["capacity"]
        self.rental_methods = parsed["rental_methods"]


"""
d = {
    "station_id": "11",
    "num_vehicles_available": 1,
    "vehicle_types_available": [
        {
            "vehicle_type_id": "mechanical",
            "count": 0
        },
        {
            "vehicle_type_id": "electrical",
            "count": 1
        }
    ],
    "num_vehicles_disabled": 3,
    "num_docks_available": 16,
    "num_docks_disabled": 1,
    "is_installed": true,
    "is_renting": true,
    "is_returning": true,
    "last_reported": "2026-06-22T06:44:33Z"
}
"""

def refresh_status(func):
    def wrapper(self):
        station_status = get_data_with_cache(self._station_status_url, ttl=DEFAULT_STATION_STATUS_TTL)
        for station_dict in station_status["data"]["stations"]:
            if station_dict["station_id"] == self.id:
                parsed = parse_station_status_dict(station_dict)
                break
        else:
            raise ValueError(f"Couldn't retrieve station status for station {self.id}")
        self._bikes_available = parsed["bikes_available"]
        self._bikes_disabled = parsed["bikes_disabled"]
        self._docks_available = parsed["docks_available"]
        self._docks_disabled = parsed["docks_disabled"]
        self._mechanical_bikes = parsed["mechanical_bikes"]
        self._electrical_bikes = parsed["electrical_bikes"]
        self._is_renting = parsed["is_renting"]
        self._is_returning = parsed["is_returning"]
        self._last_reported = parsed["last_reported"]
        return func(self)
    return wrapper


def parse_station_status_dict(d: dict) -> dict:
    _id = d["station_id"]
    _bikes_available = int(d["num_vehicles_available"])
    _bikes_disabled = int(d["num_vehicles_disabled"])
    _docks_available = int(d["num_docks_available"])
    _docks_disabled = int(d["num_docks_disabled"])
    _mechanical_bikes, _electrical_bikes = 0, 0  # Default values
    for vehicle_type_dict in d["vehicle_types_available"]:
        match vehicle_type_dict["vehicle_type_id"]:
            case "mechanical":
                _mechanical_bikes = int(vehicle_type_dict["count"])
            case "electrical":
                _electrical_bikes = int(vehicle_type_dict["count"])
    # _is_installed = bool(d["is_installed"])
    _is_renting = bool(d["is_renting"])
    _is_returning = bool(d["is_returning"])
    _last_reported_str = d["last_reported"]
    _last_reported = datetime.fromisoformat(_last_reported_str.replace("Z", "+00:00"))
    return {
        "id": _id,
        "bikes_available": _bikes_available,
        "bikes_disabled": _bikes_disabled,
        "docks_available": _docks_available,
        "docks_disabled": _docks_disabled,
        "mechanical_bikes": _mechanical_bikes,
        "electrical_bikes": _electrical_bikes,
        "is_renting": _is_renting,
        "is_returning": _is_returning,
        "last_reported": _last_reported,
    }


@dataclass
class StationStatus:
    id: str
    _station_status_url: str
    _bikes_available: int = None
    _bikes_disabled: int = None
    _docks_available: int = None
    _docks_disabled: int = None
    _mechanical_bikes: int = None
    _electrical_bikes: int = None
    _is_renting: bool = None
    _is_returning: bool = None
    _last_reported: datetime = None

    @classmethod
    def from_dict(cls, d, _station_status_url: str):
        parsed = parse_station_status_dict(d)
        return cls(
            parsed["id"],
            _station_status_url,
            parsed["bikes_available"],
            parsed["bikes_disabled"],
            parsed["docks_available"],
            parsed["docks_disabled"],
            parsed["mechanical_bikes"],
            parsed["electrical_bikes"],
            parsed["is_renting"],
            parsed["is_returning"],
            parsed["last_reported"]
        )

    @property
    @refresh_status
    def bikes_available(self):
        return self._bikes_available

    @property
    @refresh_status
    def bikes_disabled(self):
        return self._bikes_disabled

    @property
    @refresh_status
    def docks_available(self):
        return self._docks_available

    @property
    @refresh_status
    def docks_disabled(self):
        return self._docks_disabled

    @property
    @refresh_status
    def mechanical_bikes(self):
        return self._mechanical_bikes

    @property
    @refresh_status
    def electrical_bikes(self):
        return self._electrical_bikes

    @property
    @refresh_status
    def is_renting(self):
        return self._is_renting

    @property
    @refresh_status
    def is_returning(self):
        return self._is_returning

    @property
    @refresh_status
    def last_reported(self):
        return self._last_reported


"""
d = {
    "vehicle_type_id": "mechanical",
    "form_factor": "bicycle",
    "propulsion_type": "human",
    "name": [
        {
            "text": "vélôToulouse",
            "language": "fr"
        },
        {
            "text": "vélôToulouse",
            "language": "en"
        },
        {
            "text": "vélôToulouse",
            "language": "es"
        }
    ],
    "max_range_meters": 0,
    "default_reserve_time": 900,
    "return_constraint": "any_station"
}
"""

@dataclass
class VehicleType:
    id: str
    propulsion_type: str
    max_range_meters: int

    @classmethod
    def from_dict(cls, d, language: str="fr"):
        _id = d["vehicle_type_id"]
        _propulsion_type = d["propulsion_type"]
        _max_range_meters = int(d["max_range_meters"])