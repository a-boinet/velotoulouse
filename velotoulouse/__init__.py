GBFS_FEEDS_URL = "https://api.cyclocity.fr/contracts/toulouse/gbfs/v3/gbfs.json"

SUPPORTED_LANGUAGES = {"fr", "en", "es"}  # TODO Fetch it from https://api.cyclocity.fr/contracts/toulouse/gbfs/v3/system_information.json instead

DEFAULT_RETRIES = 3

from .client import VeloToulouseClient