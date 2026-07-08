from velotoulouse import VeloToulouseClient


if __name__ == "__main__":
    with VeloToulouseClient(language="fr") as client:  # Client handles context manager
        stations_list: list = client.get_stations()
        stations_dict: dict = client.get_stations_dict()
        station = client.get_station("1")
        print(f"{station.bikes_available} vélos sont disponibles à la station {station.name} (id {station.id}), dont:")
        print(f" - {station.mechanical_bikes} vélos mécaniques")
        print(f" - {station.electrical_bikes} vélos électriques")

