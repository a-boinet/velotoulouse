import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from velotoulouse import DEFAULT_RETRIES
from velotoulouse.exceptions import APIError, InvalidFeedError


@dataclass
class Feed:
    url: str
    ttl: int = 0
    latest_update: datetime = None
    data: dict = field(default_factory=dict)


class ClientCache:
    def __init__(self, feeds_url: dict[str, str]):
        self._feeds = {
            feed_name: Feed(url) for feed_name, url in feeds_url.items()
        }
        self._client = httpx.Client()

    def add_feed(self, feed_name: str, feed_url: str):
        self._feeds[feed_name] = Feed(feed_url)

    def _get(self, feed_name: str, url: str, retries: int = DEFAULT_RETRIES) -> dict[str, Any]:
        for attempt in range(retries + 1):
            try:
                response = self._client.get(url)
                response.raise_for_status()
                return response.json()

            # Deal with network issues
            except (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
            ) as e:
                if attempt == retries:
                    raise APIError(f"Couldn't fetch '{feed_name}' data from {url}") from e
                print(f"Couldn't fetch '{feed_name}' data, retrying...")  # TODO Use logging module
                time.sleep(0.5 * 2**attempt)

            # Deal with HTTP status errors
            except httpx.HTTPStatusError as e:
                raise APIError(
                    f"Couldn't fetch '{feed_name}' data from {url} "
                    f"(HTTP code {e.response.status_code})"
                ) from e

            # Deal with JSON parsing errors
            except (json.decoder.JSONDecodeError, ValueError) as e:
                raise APIError(f"Couldn't parse '{feed_name}' data from {url}") from e

        raise APIError(f"Feed '{feed_name}' at {url} is unreachable")

    def get_feed(self, feed_name: str) -> dict:
        if feed_name not in self._feeds:
            raise InvalidFeedError(feed_name, self._feeds.keys())  # NOQA

        feed = self._feeds[feed_name]
        current_time = datetime.now(tz=timezone.utc)

        if feed.latest_update is not None and (current_time - feed.latest_update).total_seconds() < feed.ttl:
            # The cache is still valid
            return feed.data

        # Let's fetch some fresh data
        data = self._get(feed_name, feed.url)

        feed.ttl = data.get('ttl', 0)
        feed.latest_update = current_time
        feed.data = data

        return data

    def get_station_information_index(self):
        station_information = self.get_feed("station_information")
        # TODO Cache this dict too
        return {
            station["station_id"]: {**station, "last_updated": station_information["last_updated"]}
            for station in station_information["data"]["stations"]
        }

    def get_station_status_index(self):
        station_status = self.get_feed("station_status")
        # TODO Cache this dict too
        return {
            station["station_id"]: {**station, "last_updated": station_status["last_updated"]}
            for station in station_status["data"]["stations"]
        }

    def refresh(self, target: str = "all"):
        if target == "all":
            selected = self._feeds.keys()
        else:
            selected = [target]  # Nothing happens if the target is invalid

        for feed_name, feed in self._feeds.items():
            if feed_name in selected:
                data = self._get(feed_name, feed.url)
                feed.ttl = data.get('ttl', 0)
                feed.latest_update = datetime.now(tz=timezone.utc)
                feed.data = data

    def close(self):
        self._client.close()
