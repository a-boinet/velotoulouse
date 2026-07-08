class VeloToulouseError(Exception):
    """
    Base exception class
    """

class LanguageNotSupportedError(VeloToulouseError):
    def __init__(self, language: str, supported_languages: set[str]):
        self.language = language
        self.supported_languages = sorted(supported_languages)  # To keep order consistent
        super().__init__(
            f"Unsupported language '{self.language}' "
            f"(supported languages: {', '.join(self.supported_languages)})"
        )

class InvalidFeedError(VeloToulouseError):
    def __init__(self, feed: str, available_feeds: list[str]):
        self.feed = feed
        self.available_feeds = sorted(available_feeds)
        super().__init__(
            f"Feed '{self.feed}' is unavailable "
            f"(available feeds: {', '.join(self.available_feeds)})"
        )

class StationNotFoundError(VeloToulouseError):
    def __init__(self, station_id: str):
        self.station_id = station_id
        super().__init__(f"Couldn't find station with id {station_id}")

class APIError(VeloToulouseError):
    pass