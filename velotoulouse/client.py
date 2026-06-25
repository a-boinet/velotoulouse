from velotoulouse import BASE_URL, DEFAULT_GBFS_FEED_TTL
from velotoulouse.models import Station, StationInformation, StationStatus
from velotoulouse.utils import get_data_with_cache


class VeloToulouseClient:
    def __init__(self, language: str="fr"):
        match language:
            case "fr":
                self.language = "fr"
            case "en":
                self.language = "en"
            case "es":
                self.language = "es"
            case _:
                raise ValueError(f"Unsupported language '{language}'")

        # Get GBFS feed
        gbfs_feeds: dict[str, str] = {
            feed["name"]: feed["url"]
            for feed
            in get_data_with_cache(
                f"{BASE_URL}/gbfs.json", ttl=DEFAULT_GBFS_FEED_TTL
            )["data"]["feeds"]
        }


        # Station information
        if "station_information" not in gbfs_feeds:
            raise Exception("Couldn't retrieve station information")
        self._station_information_url = gbfs_feeds["station_information"]

        # Station status
        if "station_status" not in gbfs_feeds:
            raise Exception("Couldn't retrieve station status")
        self._station_status_url = gbfs_feeds["station_status"]

        # We only keep station information.
        # The TTL for station status is too short,
        # so we have to recompute it each time
        self._station_information: dict[str, StationInformation] = {}

    @property
    def stations(self) -> list[Station]:
        self._refresh_station_information()
        stations = []
        for station_id, station_information in self._station_information.items():
            stations.append(
                Station(
                    _station_information=station_information,
                    _station_status=StationStatus(station_id, self._station_status_url)
                )
            )
        return stations

    @property
    def stations_dict_by_id(self) -> dict[str, Station]:
        return {s.id: s for s in self.stations}

    @property
    def stations_dict_by_name(self) -> dict[str, Station]:
        return {s.name: s for s in self.stations}

    def _refresh_station_information(self):
        station_information = get_data_with_cache(self._station_information_url, ttl=300)
        if "data" not in station_information or "stations" not in station_information["data"]:
            raise Exception(f"Couldn't retrieve station information")
        for station_dict in station_information["data"]["stations"]:
            station_id = station_dict["station_id"]
            self._station_information[station_id] = StationInformation.from_dict(station_dict, language=self.language)

    def refresh(self):
        self._refresh_station_information()

    def get_station(self, station_id: str) -> Station:
        """
        Get a station by its id
        :param station_id:
        :return: A Station object
        """
        station_information = get_data_with_cache(self._station_information_url, ttl=300)
        for station_dict in station_information["data"]["stations"]:
            if station_dict["station_id"] == station_id:
                target_station_dict = station_dict
                break
        else:
            raise Exception(f"Couldn't find station with id {station_id}")

        if station_id not in self._station_information:
            self._station_information[station_id] = StationInformation.from_dict(target_station_dict, language=self.language)
        else:
            # Refresh it, just in case
            self._station_information[station_id].refresh(target_station_dict)
        return Station(
            _station_information=self._station_information[station_id],
            _station_status=StationStatus(station_id, self._station_status_url)
        )
