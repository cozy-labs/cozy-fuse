import pytest
import sys
import os

from uuid import uuid4

sys.path.append('..')

import cozyfuse.local_config as local_config
import cozyfuse.binarycache as binarycache

local_config.CONFIG_FOLDER = \
    os.path.join(os.path.expanduser('~'), '.cozyfuse-test')

local_config.CONFIG_PATH = \
    os.path.join(local_config.CONFIG_FOLDER, 'config.yaml')


import cozyfuse.dbutils as dbutils

TESTDB = 'cozy-fuse-test'
MOUNT_FOLDER = os.path.join(os.path.expanduser('~'), TESTDB)
DEVICE_CONFIG_PATH = os.path.join(local_config.CONFIG_FOLDER, TESTDB)
CACHE_FOLDER = os.path.join(DEVICE_CONFIG_PATH, 'cache')
COUCH_URL = 'http://login:password@localhost:5984/cozy-fuse-test'
BINARY_ID = uuid4().hex
FILE_ID = uuid4().hex


@pytest.fixture(scope="module")
def config_db(request):
    filename = local_config.CONFIG_PATH
    with file(filename, 'a'):
        os.utime(filename, None)

    name = TESTDB
    url = 'https://localhost:2223'
    path = '/home/myself/cozyfiles'
    db_login = 'login'
    db_password = 'password'
    dbutils.create_db(name)
    dbutils.create_db_user(name, db_login, db_password)
    local_config.add_config(name, url, path, db_login, db_password)
    db = dbutils.get_db(name)
    dbutils.init_database_views(name)

    binary = {
       '_id': BINARY_ID,
        'docType': 'Binary',
    }
    db.save(binary)
    db.put_attachment(binary, open('./file_test.txt'), 'file')

    testfile = {
        '_id': FILE_ID,
        'docType': 'File',
        'path': '/tests',
        'name': 'file_test.txt',
        'binary': { 'file': { 'id': BINARY_ID } }
    }
    db.save(testfile)

    def fin():
        dbutils.remove_db(name)
    request.addfinalizer(fin)

def test_constructor():
    binary_cache = binarycache.BinaryCache(
        TESTDB, DEVICE_CONFIG_PATH, COUCH_URL , MOUNT_FOLDER)
    assert os.path.isdir(os.path.join(DEVICE_CONFIG_PATH, 'cache'))
    assert binary_cache.metadata_cache is not None


def test_get_file_metadata(config_db):
    binary_cache = binarycache.BinaryCache(
        TESTDB, DEVICE_CONFIG_PATH, COUCH_URL, MOUNT_FOLDER)
    (cached_file, bin_id, cache_path) = \
        binary_cache.get_file_metadata('/tests/file_test.txt')
    assert bin_id == BINARY_ID
    assert cached_file['_id'] == FILE_ID
    cache_file_folder = os.path.join(CACHE_FOLDER, BINARY_ID)
    cache_file_name = os.path.join(cache_file_folder, 'file')
    assert cache_path == cache_file_name

def test_cache():
    binary_cache = binarycache.BinaryCache(
        TESTDB, DEVICE_CONFIG_PATH, COUCH_URL, MOUNT_FOLDER)
    binary_cache.add('/tests/file_test.txt')
    assert binary_cache.is_cached('/tests/file_test.txt')

    binary_cache.remove('/tests/file_test.txt')
    assert not binary_cache.is_cached('/tests/file_test.txt')

def test_mark_file_as_stored():
    db = dbutils.get_db(TESTDB)
    file_doc = db.get(FILE_ID)
    assert file_doc['storage'] == []
    binary_cache = binarycache.BinaryCache(
        TESTDB, DEVICE_CONFIG_PATH, COUCH_URL, MOUNT_FOLDER)
    binary_cache.mark_file_as_stored(file_doc)
    assert file_doc['storage'] == ['cozy-fuse-test']
    binary_cache.mark_file_as_not_stored(file_doc)
    assert file_doc['storage'] == []
