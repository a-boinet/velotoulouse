from collections import namedtuple
from datetime import datetime, timezone

import requests

TimestampedData = namedtuple("TimestampedData", "timestamp data")

LAST_UPDATED_DICT: dict[str, TimestampedData] = {}

def get_data_with_cache(url: str, ttl: int) -> dict:
    current_time = datetime.now(tz=timezone.utc)
    if url in LAST_UPDATED_DICT and (current_time - LAST_UPDATED_DICT[url].timestamp).seconds < ttl:
        return LAST_UPDATED_DICT[url].data
    data = requests.get(url).json()
    # We recompute it, in case the request took too long
    current_time = datetime.now(tz=timezone.utc)
    LAST_UPDATED_DICT[url] = TimestampedData(timestamp=current_time, data=data)
    return data