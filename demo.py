from velotoulouse import VeloToulouseClient


if __name__ == "__main__":
    client = VeloToulouseClient()
    stations = client.stations
    stations_dict = client.stations_dict_by_name
    station = client.get_station("1")
    print(f"Bikes available at station '{station.name}': {station.bikes_available}")
