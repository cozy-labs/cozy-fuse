import pytest
import sys
import os
import requests

sys.path.append('..')

import cozyfuse.local_config as local_config
local_config.CONFIG_FOLDER = \
    os.path.join(os.path.expanduser('~'), '.cozyfuse-test')

local_config.CONFIG_PATH = \
    os.path.join(local_config.CONFIG_FOLDER, 'config.yaml')


import cozyfuse.dbutils as dbutils

TESTDB = 'cozy-fuse-test'


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
    local_config.add_config(name, url, path, db_login, db_password)


def test_get_db(config_db):
    db = dbutils.get_db(TESTDB)
    assert db is not None


def test_get_db_and_server():
    (db, server) = dbutils.get_db_and_server(TESTDB)
    assert db is not None
    assert server is not None
    assert db.info()["db_name"] == TESTDB


def _create_device_view():
    pass


def test_get_random_key():
    key1 = dbutils.get_random_key()
    key2 = dbutils.get_random_key()
    assert len(key1) is 20
    assert len(key2) is 20
    assert key1 is not key2


def test_create_db_user():
    db_login = 'login'
    db_password = 'password'
    dbutils.create_db_user(TESTDB, db_login, db_password)
    response = requests.get(
        'http://localhost:5984/_users/org.couchdb.user:%s' % db_login)
    assert response.status_code == 200


def test_init_dabase_view():
    db = dbutils.get_db(TESTDB)
    dbutils.init_database_view('MyDocType', db)
    view = db["_design/mydoctype"]
    assert 'all' in view['views']
    assert 'byFolder' in view['views']
    assert 'byFullPath' in view['views']


def init_dabase_views():
    pass


def get_device():
    device = {
        'url': 'https://test.cozycloud.cc',
        'folder': '/home/cozy',
        'name': TESTDB,
        'configuration': ["File", "Folder"],
    }
    db = dbutils.get_db(TESTDB)
    db.create(device)


def init_db():
    pass



def test_remove_db():
    dbutils.remove_db(TESTDB)
    db = dbutils.get_db(TESTDB)
    assert db is None


def test_remove_db_user():
    db_login = 'login'
    dbutils.remove_db_user(db_login)
    response = requests.get(
        'http://localhost:5984/_users/org.couchdb.user:%s' % db_login)
    assert response.status_code == 404


def test_clear_config():
    local_config.clear()
