import datetime

VALIDITY_PERIOD = datetime.timedelta(seconds=30)


class Cache:
    '''
    Utility to store data in memory for a short time and retrieve them quickly.
    '''

    def __init__(self, validity_period=VALIDITY_PERIOD):
        '''
        Initialize cache dict one for the data to store, the other one to store
        validity time stamps.
        '''
        self._cache = {}
        self._timestamps = {}
        self.validity_period = validity_period

    def get(self, key):
        '''
        Return value corresponding to given key from cache if it is present
        and the validity period is not expired.
        '''
        now = datetime.datetime.now()
        if self._timestamps.get(key, now) > now:
            return self._cache[key]
        else:
            self.remove(key)
            return None

    def add(self, key, value):
        '''
        Add a key/value couple to the cache that will be valing for defined
        validity period.
        '''
        now = datetime.datetime.now()
        self._cache[key] = value
        self._timestamps[key] = now + self.validity_period

    def remove(self, key):
        '''
        Remove couple key/value from cache.
        '''
        if key in self._cache:
            del self._cache[key]
        if key in self._timestamps:
            del self._timestamps[key]
