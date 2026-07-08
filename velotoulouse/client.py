from datetime import datetime

from velotoulouse import GBFS_FEEDS_URL, SUPPORTED_LANGUAGES
from velotoulouse.exceptions import APIError, StationNotFoundError, LanguageNotSupportedError
from velotoulouse.models import Station
from velotoulouse.cache import ClientCache


class VeloToulouseClient:
    def __init__(self, language: str="fr"):
        if language.lower() not in SUPPORTED_LANGUAGES:
            raise LanguageNotSupportedError(language.lower(), supported_languages=SUPPORTED_LANGUAGES)
        self.language = language.lower()

        self._cache = ClientCache({"gbfs_feeds": GBFS_FEEDS_URL})
        self._stations: dict[str, Station] = {}

        # Get GBFS feed (and cache it)
        gbfs_feeds: dict[str, str] = {
            feed["name"]: feed["url"]
            for feed
            in self._cache.get_feed("gbfs_feeds")["data"]["feeds"]
        }

        # Sanity checks
        for feed_name in ["station_information", "station_status"]:
            if feed_name not in gbfs_feeds:
                raise APIError(f"Couldn't fetch '{feed_name}' feed url")

        # Instantiate cache for all feeds
        for feed_name, feed_url in gbfs_feeds.items():
            self._cache.add_feed(feed_name, feed_url)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _get_station_dict(self, feed_name: str):
        station_dict = self._cache.get_feed(feed_name)
        return {
            station["station_id"]: {**station, "last_reported": station_dict["last_reported"]}
            for station in station_dict["data"]["stations"]
        }

    def _get_station_indexes(self):
        return (
            self._cache.get_station_information_index(),
            self._cache.get_station_status_index()
        )

    def _parse_station_data(
        self,
        station_id: str,
        station_information_indexes: dict,
        station_status_indexes: dict
    ):
        if station_id not in station_information_indexes or station_id not in station_status_indexes:
            raise StationNotFoundError(station_id)

        station_information = station_information_indexes[station_id]
        station_status = station_status_indexes[station_id]

        station_name = station_information["name"][0]["text"]  # Default language (fallback if target language is unavailable)
        for name_dict in station_information["name"][1:]:
            if name_dict["language"] == self.language:
                station_name = name_dict["text"]

        vehicle_counts = {
            vehicle_type["vehicle_type_id"]: vehicle_type["count"]
            for vehicle_type in station_status["vehicle_types_available"]
        }
        return {
            "id": station_information["station_id"],
            "name": station_name,
            "latitude": station_information["lat"],
            "longitude": station_information["lon"],
            "address": station_information["address"],
            "rental_methods": station_information.get("rental_methods", []),
            "capacity": station_information["capacity"],
            "bikes_available": station_status["num_vehicles_available"],
            "bikes_disabled": station_status["num_vehicles_disabled"],
            "docks_available": station_status["num_docks_available"],
            "docks_disabled": station_status["num_docks_disabled"],
            "mechanical_bikes": vehicle_counts.get("mechanical", 0),
            "electrical_bikes": vehicle_counts.get("electrical", 0),
            "is_renting": station_status["is_renting"],
            "is_returning": station_status["is_returning"],
            "last_reported": datetime.fromisoformat(station_status["last_reported"].replace("Z", "+00:00")),
            "last_updated": datetime.fromisoformat(station_status["last_updated"].replace("Z", "+00:00")),
        }

    def _build_station(
        self,
        station_id: str,
        station_information_indexes: dict,
        station_status_indexes: dict
    ) -> Station:
        merged_info_and_status = self._parse_station_data(
            station_id, station_information_indexes, station_status_indexes
        )
        return Station(
            **merged_info_and_status,
            _client=self,
        )

    def _update_station(
        self,
        station: Station,
        station_information_indexes: dict,
        station_status_indexes: dict
    ):
        merged_info_and_status = self._parse_station_data(
            station.id, station_information_indexes, station_status_indexes
        )
        if station.id != merged_info_and_status["id"]:
            raise StationNotFoundError(station.id)

        merged_info_and_status.pop("id")  # Don't refresh the id
        for key, value in merged_info_and_status.items():
            setattr(station, key, value)

    def get_station(self, station_id: str | int) -> Station:
        """
        Get a station by its id
        :param station_id: Either a str or int
        :return: A Station object
        """
        if isinstance(station_id, int):
            station_id = str(station_id)

        station_information_indexes, station_status_indexes = self._get_station_indexes()

        if station_id in self._stations:
            # We already cached this station, let's just refresh its information
            station = self._stations[station_id]
            self._update_station(station, station_information_indexes, station_status_indexes)
            return self._stations[station_id]

        # That's the first time we're asked about this station, so let's cache it
        station = self._build_station(station_id, station_information_indexes, station_status_indexes)
        self._stations[station.id] = station
        return station

    def get_stations(self) -> list[Station]:
        """
        Get all stations as a list of Station objects
        :return: A list of Station objects
        """
        station_information_indexes, station_status_indexes = self._get_station_indexes()

        for station_id in station_information_indexes.keys():
            if station_id not in station_status_indexes:
                # We have the station information but no status
                raise StationNotFoundError(station_id)

            if station_id not in self._stations:
                # New station, build it
                self._stations[station_id] = self._build_station(
                    station_id, station_information_indexes, station_status_indexes
                )
            else:
                # Refresh the station
                self._update_station(
                    self._stations[station_id], station_information_indexes, station_status_indexes
                )
        return list(self._stations.values())

    def get_stations_dict(self):
        """
        Get all stations as a dict of key:station id and value:Station object
        :return: A dict of {station_id: station}
        """
        return {station.id: station for station in self.get_stations()}

    def refresh_station(self, station: Station):
        """
        Refresh station data (information + status)
        :param station:
        :return:
        """
        self._update_station(station, *self._get_station_indexes())

    def refresh(self, target: str = "all"):
        """
        Refresh cache for a given target
        :param target: "all" | "station_information" | "station_status"
        :return:
        """
        self._cache.refresh(target)

    def close(self):
        """
        Close the client
        (automatically called when using a context manager)
        :return:
        """
        self._cache.close()
