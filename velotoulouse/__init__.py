BASE_URL = "https://api.cyclocity.fr/contracts/toulouse/gbfs/v3"
DEFAULT_GBFS_FEED_TTL = 3600
DEFAULT_STATION_STATUS_TTL = 2  # In seconds


from .client import VeloToulouseClient