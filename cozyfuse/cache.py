import datetime

VALIDITY_PERIOD = datetime.timedelta(seconds=30)


class Cache:

    def __init__(self, validity_period=VALIDITY_PERIOD):
        self._cache = {}
        self._timestamps = {}
        self.validity_period = validity_period

    def get(self, key):
        now = datetime.datetime.now()
        if self._timestamps.get(key, now) > now:
            return self._cache[key]
        else:
            if key in self._cache:
                del self._cache[key]
            if key in self._timestamps:
                del self._timestamps[key]
            return None

    def add(self, key, value):
        now = datetime.datetime.now()
        self._cache[key] = value
        self._timestamps[key] = now + self.validity_period

    def remove(self, key, value):
        if key in self._cache:
            del self._cache[key]
        if key in self._timestamps:
            del self._timestamps[key]
