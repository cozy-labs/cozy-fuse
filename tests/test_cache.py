import pytest
import sys
import datetime
import time


sys.path.append('..')

import cozyfuse.cache as cache


def test_add():
    local_cache = cache.Cache()
    assert local_cache.get('test') is None
    local_cache.add('test', 42)
    assert local_cache.get('test') == 42

def test_remove():
    local_cache = cache.Cache()
    local_cache.add('test', 42)
    assert local_cache.get('test') == 42
    local_cache.remove('test')
    assert local_cache.get('test') is None

def test_invalidity():
    local_cache = cache.Cache(datetime.timedelta(seconds=1))
    local_cache.add('test', 42)
    assert local_cache.get('test') == 42
    time.sleep(1)
    assert local_cache.get('test') is None
